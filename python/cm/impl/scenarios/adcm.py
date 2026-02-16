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

import logging

from adcm_version import compare_prototype_versions
from core.scenarios.adcm import InitializeADCM, UpgradeADCM
from core.types import ADCMCoreType, BundleID, ConfigID, CoreObjectDescriptor

from cm.legacy.bundle_switch_revert import switch_config
from cm.models import ADCM, ConfigLog, ObjectConfig, Prototype

logger = logging.getLogger("adcm")

# todo whole implementation shouldn't be kept in here, so such override won't be required


class InitializeADCMLegacy(InitializeADCM):
    def do(self, bundle_id: BundleID):
        prototype = Prototype.objects.get(bundle_id=bundle_id, type="adcm")
        adcm = ADCM.objects.create(prototype=prototype, name="ADCM")
        descriptor = CoreObjectDescriptor(id=adcm.pk, type=ADCMCoreType.ADCM)
        specification, defaults = self.config_service.retrieve_specification_with_defaults(owner=descriptor)
        config_id = self.config_service.create_initial_configuration(
            owner=descriptor, specification=specification, defaults=defaults
        )
        if self.default_adcm_url:
            _set_adcm_url(config_id=config_id, adcm_url=self.default_adcm_url)


class UpgradeADCMLegacy(UpgradeADCM):
    def do(self, bundle_id: BundleID):
        new_prototype = Prototype.objects.get(bundle_id=bundle_id, type="adcm")

        adcm = ADCM.objects.get()
        old_prototype = adcm.prototype

        adcm.prototype = new_prototype
        adcm.save(update_fields=["prototype"])

        switch_config(
            obj=adcm, new_prototype=new_prototype, old_prototype=old_prototype, config_service=self.config_service
        )

        _adcm_config_data_migration(
            adcm_config=adcm.config, old_version=old_prototype.version, new_version=new_prototype.version
        )


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


def _set_adcm_url(config_id: ConfigID, adcm_url: str) -> None:
    config_log = ConfigLog.objects.get(id=config_id)
    config_log.config["global"]["adcm_url"] = adcm_url
    config_log.save(update_fields=["config"])
    logger.info("Set ADCM's URL from environment variable: %s", adcm_url)
