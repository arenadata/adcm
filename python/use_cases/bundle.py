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

from dataclasses import dataclass
from pathlib import Path
import logging

from adcm_version import ComparisonResult, compare_adcm_versions
from cm import models
from cm.errors import AdcmEx
from cm.legacy.services import adcm
from cm.legacy.services import bundle_alt as bundle
from core.errors import localize_error
from core.files import directories
from core.scenarios.adcm import InitializeADCM, UpgradeADCM
from core.settings import Directories
from core.types import BundleID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios
import core

logger = logging.getLogger("adcm")


@dataclass(slots=True)
class ParseBundleFromRequest:
    directories: Directories

    bundle_service: core.bundle.BundleService
    rbac_scenarios: RBACScenarios

    @bundle.errors.convert_bundle_errors_to_adcm_ex
    def do(self, archive: Path) -> BundleID:
        adcm_configuration = adcm.get_adcm_configuration()
        verified_signature_only = adcm.get_verified_bundles_flag(adcm_configuration)

        with bundle.load.cleanup(on_exit=[archive]):
            unpacking_info = bundle.load.unpack_bundle(
                archive=archive, bundles_dir=self.directories.bundles, files_dir=self.directories.files
            )
            with bundle.load.cleanup(on_fail=[unpacking_info.root]):
                bundle.load.verify_signature(unpacking_info.signature, verified_signature_only)

                with localize_error(f"Bundle from {archive.name}"):
                    root_entries = self.bundle_service.read_root_bundle_entries_from_fs(bundle_root=unpacking_info.root)
                    parsing_meta, definitions = self.bundle_service.parse_to_definitions(
                        entries=root_entries, bundle_root=unpacking_info.root
                    )

                with atomic():
                    bundle_info = core.bundle.BundleInfo.from_unpacking_info(
                        unpacking_info, contract_version=parsing_meta.contract_version
                    )
                    bundle_id = self.bundle_service.create_bundle_from_definitions(
                        definitions=definitions, bundle_info=bundle_info
                    )
                    bundle_object = models.Bundle.objects.get(id=bundle_id)
                    self.rbac_scenarios.prepare_action_roles(bundle=bundle_object)

        return bundle_id


@dataclass(slots=True)
class InitOrUpgradeADCM:
    adcm_bundle_dir: directories.ADCMBundleDir

    bundle_service: core.bundle.BundleService

    initialize_adcm: InitializeADCM
    upgrade_adcm: UpgradeADCM

    @bundle.errors.convert_bundle_errors_to_adcm_ex
    def do(
        self,
        # required for test for a while, should be changed with DI thou
        alternative_adcm_dir: Path | None = None,
    ) -> None:
        adcm_object = models.ADCM.objects.first()
        current_adcm_bundle_version = adcm_object.prototype.version if adcm_object is not None else "0"
        bundle_root = alternative_adcm_dir or self.adcm_bundle_dir

        root_entries = self.bundle_service.read_root_bundle_entries_from_fs(bundle_root=bundle_root)
        parsing_meta, definitions = self.bundle_service.parse_to_definitions(
            entries=root_entries, bundle_root=bundle_root
        )

        new_adcm_bundle_version = definitions[("adcm",)].version
        match compare_adcm_versions(this=current_adcm_bundle_version, other=new_adcm_bundle_version):
            case ComparisonResult.EQUAL:
                return

            case ComparisonResult.NEWER:
                msg = (
                    f"Current adcm version {current_adcm_bundle_version} is higher "
                    f"than upgrade version {new_adcm_bundle_version}."
                )
                raise AdcmEx(code="UPGRADE_ERROR", msg=msg)

        with atomic():
            bundle_info = core.bundle.BundleInfo(
                contract_version=parsing_meta.contract_version,
                hash="adcm",
                root=bundle_root,
                signature=core.bundle.SignatureStatus.ABSENT,
            )
            bundle_id = self.bundle_service.create_bundle_from_definitions(
                definitions=definitions, bundle_info=bundle_info
            )
            match adcm_object:
                case models.ADCM():
                    self.upgrade_adcm.do(bundle_id=bundle_id)

                    self.bundle_service.clear_old_versions_adcm_bundles()

                    logger.info("ADCM upgrade: OK (%s -> %s).", current_adcm_bundle_version, new_adcm_bundle_version)

                case None:
                    self.initialize_adcm.do(bundle_id=bundle_id)

                    logger.info("ADCM upgrade: version %s initialized.", new_adcm_bundle_version)


@dataclass(slots=True)
class AcceptLicense:
    bundle_service: core.bundle.BundleService

    @bundle.errors.convert_bundle_errors_to_adcm_ex
    def do(self, prototype: models.Prototype) -> None:
        meta_info = core.bundle.d.PrototypeMetaInfo(
            contract_version=prototype.bundle.contract_version,
            license=core.bundle.d.License(
                status=prototype.license,
                path=prototype.license_path,
                hash=prototype.license_hash,
            ),
        )

        self.bundle_service.accept_license(prototype_meta_info=meta_info)
