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
import shutil

from cm.models import Bundle
from core.bundle import get_hash_safe, untar_safe
from django.conf import settings
from rest_framework.response import Response
from rest_framework.status import HTTP_409_CONFLICT
from tests.suites import ADCMDjangoAPISuite
from tests.use_cases import prepare_bundle_file
from unittest_parametrize import parametrize

ALREADY_EXISTS_MESSAGE = "Bundle already exists"
UNSUPPORTED_CONTRACT_MESSAGE = "Unsupported bundle's prototype usage"

REJECTED_BUNDLES = ("newer_adcm_min_version", "unsupported_contract_version")


class TestBundleUploadExistenceCheck(ADCMDjangoAPISuite):
    """
    ADCM-8528
    Checks order:
        - bundle existence (download dir / bundles dir / DB hash / DB name-version-edition)
        - contract version
        - minimal ADCM version

    Emulates ADCM started with data volume that doesn't match DB.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundles_dir = cls.test_bundles_dir / "adcm_8528"

    def prepare_archive(self, source_dir_name: str) -> Path:
        return prepare_bundle_file(source_dir=self.bundles_dir / source_dir_name, target_dir=self.directories.temp)

    def upload_bundle_r(self, archive: Path) -> Response:
        with archive.open(encoding=settings.ENCODING_UTF_8) as file_:
            return (self.client.v2 / "bundles").post(data={"file": file_}, format_="multipart")

    def assert_already_exists(self, response: Response) -> None:
        response_data = response.json()
        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response_data)
        self.assertEqual(response_data["code"], "BUNDLE_ERROR", response_data)
        self.assertIn(ALREADY_EXISTS_MESSAGE, response_data["desc"], response_data)

    @parametrize("source_dir_name", REJECTED_BUNDLES, ids=REJECTED_BUNDLES)
    def test_archive_in_downloads_not_in_db_fail(self, source_dir_name: str):
        archive = self.prepare_archive(source_dir_name)
        old_archive = shutil.copy(archive, self.directories.downloads / "old_upload.tar")
        self.addCleanup(Path(old_archive).unlink, missing_ok=True)

        response = self.upload_bundle_r(archive)

        self.assert_already_exists(response)
        self.assertFalse(Bundle.objects.filter(name="cluster_adcm_8528").exists())

    @parametrize("source_dir_name", REJECTED_BUNDLES, ids=REJECTED_BUNDLES)
    def test_bundle_dir_on_disk_not_in_db_fail(self, source_dir_name: str):
        archive = self.prepare_archive(source_dir_name)
        bundle_dir = self.directories.bundles / get_hash_safe(archive)
        untar_safe(to=bundle_dir, tar_from=archive)
        self.addCleanup(shutil.rmtree, bundle_dir, ignore_errors=True)

        response = self.upload_bundle_r(archive)

        self.assert_already_exists(response)
        self.assertFalse(Bundle.objects.filter(name="cluster_adcm_8528").exists())
        # bundle dir wasn't created by this upload, so it shouldn't be removed on failure
        self.assertTrue(bundle_dir.is_dir())

    @parametrize("source_dir_name", REJECTED_BUNDLES, ids=REJECTED_BUNDLES)
    def test_same_hash_in_db_not_on_disk_fail(self, source_dir_name: str):
        archive = self.prepare_archive(source_dir_name)
        existing = Bundle.objects.create(name="other_cluster", version="2.0", hash=get_hash_safe(archive))

        response = self.upload_bundle_r(archive)

        self.assert_already_exists(response)
        self.assertIn(
            f"Name: {existing.name}, version: {existing.version}, edition: {existing.edition}",
            response.json()["desc"],
        )
        self.assertFalse(Bundle.objects.filter(name="cluster_adcm_8528").exists())

    @parametrize("source_dir_name", REJECTED_BUNDLES, ids=REJECTED_BUNDLES)
    def test_same_name_version_edition_in_db_not_on_disk_fail(self, source_dir_name: str):
        archive = self.prepare_archive(source_dir_name)
        existing = Bundle.objects.create(
            name="cluster_adcm_8528", version="1.0", edition="test-edition", hash="hash_of_other_archive"
        )

        response = self.upload_bundle_r(archive)

        self.assert_already_exists(response)
        self.assertIn(
            f"Name: {existing.name}, version: {existing.version}, edition: {existing.edition}",
            response.json()["desc"],
        )
        self.assertQuerySetEqual(Bundle.objects.filter(name="cluster_adcm_8528"), [existing])

    def test_contract_version_checked_before_adcm_min_version(self):
        archive = self.prepare_archive("unsupported_contract_version_and_newer_adcm_min_version")

        response = self.upload_bundle_r(archive)

        response_data = response.json()
        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response_data)
        self.assertEqual(response_data["code"], "BUNDLE_ERROR", response_data)
        self.assertIn(UNSUPPORTED_CONTRACT_MESSAGE, response_data["desc"], response_data)
        self.assertFalse(Bundle.objects.filter(name="cluster_adcm_8528").exists())
