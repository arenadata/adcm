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

from functools import partial
from pathlib import Path

from cm import models
from cm.services import adcm
from cm.services import bundle_alt as bundle
from django.conf import settings
from django.core.files import File
from django.db.transaction import atomic
from infra.services import get_config_service
from rbac.upgrade.role import prepare_action_roles
import core


@bundle.errors.convert_bundle_errors_to_adcm_ex
def parse_bundle_from_request_to_db(
    file_from_request: File,
) -> models.Bundle:
    adcm_configuration = adcm.get_adcm_configuration()
    verified_signature_only = adcm.get_verified_bundles_flag(adcm_configuration)

    archive = bundle.load.save_bundle_file_from_request_to_downloads(
        file_from_request=file_from_request, downloads_dir=settings.DOWNLOAD_DIR
    )

    with bundle.load.cleanup_on_fail(archive):
        unpacking_info = bundle.load.unpack_bundle(
            archive=archive, bundles_dir=settings.BUNDLE_DIR, files_dir=settings.FILE_DIR
        )
        check_defaults = partial(_check_defaults_new, bundle_root=unpacking_info.root)
        with bundle.load.cleanup_on_fail(unpacking_info.root):
            bundle.load.verify_signature(unpacking_info.signature, verified_signature_only)
            definitions = bundle.load.retrieve_bundle_definitions_from_archive(
                archive=archive,
                bundle_root=unpacking_info.root,
                adcm_version=settings.ADCM_VERSION,
                check_defaults=check_defaults,
            )

            with atomic():
                bundle_object = bundle.load.save_bundle_definitions(
                    definitions=definitions, unpacking_info=unpacking_info
                )
                prepare_action_roles(bundle=bundle_object)

    return bundle_object


@bundle.errors.convert_bundle_errors_to_adcm_ex
def process_adcm_bundle(adcm_config_file: Path) -> None:
    adcm_object = models.ADCM.objects.first()
    current_version = adcm_object.prototype.version if adcm_object is not None else "0"

    check_defaults = partial(_check_defaults_new, bundle_root=adcm_config_file.parent)

    adcm_definition = bundle.adcm.retrieve_adcm_definition(
        adcm_config_file=adcm_config_file, current_version=current_version, check_defaults=check_defaults
    )
    if adcm_definition is None:
        return

    with atomic():
        bundle.adcm.init_or_upgrade_adcm(
            adcm_definition=adcm_definition, adcm_config_file=adcm_config_file, adcm=adcm_object
        )


def _check_defaults_new(configuration: core.bundle_alt.ConfigDefinition, bundle_root: Path) -> None:
    # the whole function shouldn't be on this level,
    # but it can be moved only after direct conversion from bundle DSL to spec is available
    from cm.config.repo import build_specification_from_prototype_config_records

    # validate defaults should be added to config service, so this import won't be nessesary
    from cm.config.validators import DefaultsVariantResolver
    from cm.services.bundle_alt.repo import convert_config_definition_to_orm_model
    from core.config._pattern_validators import PossiblyEncryptedPatternValidator
    from core.result import is_fail

    secrets = get_config_service().secrets

    records = tuple(convert_config_definition_to_orm_model(configuration, prototype=None, action=None))
    specification, defaults = build_specification_from_prototype_config_records(
        records=records,
        # can't detect customization flag in here and it's not important for validation
        group_customization_flag=False,
        secrets_service=secrets,
        bundle_root=bundle_root,
    )

    flat_defaults = core.config.FlatConfiguration(
        values={k: v for k, v in defaults.items() if v is not None}, attributes={}
    )

    validators = core.config.Validators(
        variant=DefaultsVariantResolver(), pattern=PossiblyEncryptedPatternValidator(secrets=secrets)
    )

    result = core.config.operations.validate_values(
        # for now attributes feel unimportant for defaults
        configuration=flat_defaults,
        specification=specification,
        validators=validators,
    )

    if is_fail(result):
        violations_list_repr = "; ".join(f"- {v.parameter} [{v.check}]: {v.reason}" for v in result.value)
        raise bundle.errors.BundleValidationError(message=f"object's defaults are invalid: {violations_list_repr}")
