# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
import logging

from adcm_version import compare_prototype_versions
from core.bundle_alt.process import retrieve_bundle_definitions
from core.bundle_alt.types import BundleDefinitionKey, Definition
from django.db.transaction import atomic

from cm.adcm_config.config import init_object_config, switch_config
from cm.bundle import set_adcm_url
from cm.errors import AdcmEx
from cm.models import ADCM, ConfigLog, ObjectConfig, Prototype, SignatureStatus
from cm.services.bundle_alt import repo
from cm.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.services.bundle_alt.load import _get_rules_for_yspec_schema

logger = logging.getLogger("adcm")


@convert_bundle_errors_to_adcm_ex
def process_adcm_bundle(adcm_config_file: Path) -> None:
    adcm = ADCM.objects.first()
    current_version = adcm.prototype.version if adcm is not None else "0"
    is_upgrade_required = adcm is not None

    adcm_definition = _retrieve_adcm_definition(adcm_config_file=adcm_config_file, current_version=current_version)
    if adcm_definition is None:
        return

    with atomic():
        new_prototype = _prepare_adcm_prototype(definition=adcm_definition, bundle_root=adcm_config_file.parent)
        if is_upgrade_required:
            _upgrade_adcm(adcm=adcm, old_prototype=adcm.prototype, new_prototype=new_prototype)
        else:
            _init_adcm(prototype=new_prototype)


def _upgrade_adcm(adcm: ADCM, old_prototype: Prototype, new_prototype: Prototype) -> None:
    adcm.prototype = new_prototype
    adcm.save(update_fields=["prototype"])
    switch_config(obj=adcm, new_prototype=new_prototype, old_prototype=old_prototype)
    _adcm_config_data_migration(
        adcm_config=adcm.config, old_version=old_prototype.version, new_version=new_prototype.version
    )
    logger.info("ADCM upgrade: OK (%s -> %s).", old_prototype.version, new_prototype.version)


def _init_adcm(prototype: Prototype) -> None:
    adcm = ADCM.objects.create(prototype=prototype, name="ADCM")
    adcm.config = init_object_config(prototype, adcm)
    adcm.save(update_fields=["config"])
    set_adcm_url(adcm=adcm)
    logger.info("ADCM upgrade: version %s initialized.", prototype.version)


def _prepare_adcm_prototype(
    definition: dict[BundleDefinitionKey, Definition],
    bundle_root: Path,
    bundle_hash: str = "adcm",
    verification_status: SignatureStatus = SignatureStatus.ABSENT,
) -> Prototype:
    bundle = repo.save_definitions(
        bundle_definitions=definition,
        bundle_root=bundle_root,
        bundle_hash=bundle_hash,
        verification_status=verification_status,
    )
    return Prototype.objects.get(bundle=bundle)


def _retrieve_adcm_definition(
    adcm_config_file: Path, current_version: str
) -> dict[BundleDefinitionKey, Definition] | None:
    definitions = retrieve_bundle_definitions(
        bundle_dir=adcm_config_file.parent, adcm_version="0", yspec_schema=_get_rules_for_yspec_schema()
    )

    definition_version = str(definitions[("adcm",)].version)
    if _is_version_suitable(current_version=current_version, new_version=definition_version):
        return definitions

    return None


def _is_version_suitable(current_version: str, new_version: str) -> bool:
    compared = compare_prototype_versions(current_version, new_version)

    if compared == 0:
        logger.debug("ADCM upgrade: versions are equal (%s), skipping.", current_version)
        return False

    elif compared < 0:
        logger.debug("ADCM upgrade: starting upgrade from %s to %s version.", current_version, new_version)
        return True

    else:
        msg = f"Current adcm version {current_version} is higher than upgrade version {new_version}."
        raise AdcmEx(code="UPGRADE_ERROR", msg=msg)


def _adcm_config_data_migration(adcm_config: ObjectConfig, old_version: str, new_version: str) -> None:
    """Missed data migration"""

    if not (compare_prototype_versions(old_version, "2.6") <= 0 <= compare_prototype_versions(new_version, "2.7")):
        return

    config_log_old = ConfigLog.objects.get(obj_ref=adcm_config, id=adcm_config.previous)
    config_log_new = ConfigLog.objects.get(obj_ref=adcm_config, id=adcm_config.current)

    log_rotation_on_fs = config_log_old.config.get("job_log", {}).get(
        "log_rotation_on_fs", config_log_new.config["audit_data_retention"]["log_rotation_on_fs"]
    )
    config_log_new.config["audit_data_retention"]["log_rotation_on_fs"] = log_rotation_on_fs

    log_rotation_in_db = config_log_old.config.get("job_log", {}).get(
        "log_rotation_in_db", config_log_new.config["audit_data_retention"]["log_rotation_in_db"]
    )
    config_log_new.config["audit_data_retention"]["log_rotation_in_db"] = log_rotation_in_db

    config_rotation_in_db = config_log_old.config.get("config_rotation", {}).get(
        "config_rotation_in_db", config_log_new.config["audit_data_retention"]["config_rotation_in_db"]
    )
    config_log_new.config["audit_data_retention"]["config_rotation_in_db"] = config_rotation_in_db

    config_log_new.save(update_fields=["config"])
