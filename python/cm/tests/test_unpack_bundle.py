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
from tarfile import TarFile
from tempfile import gettempdir
import os
import uuid
import shutil

from api_v2.tests.base import BaseAPITestCase
from core.bundle_alt.bundle_load import get_hash_safe
from django.conf import settings

from cm.bundle import unpack_bundle


def pack_bundle(from_dir: Path, to: Path) -> Path:
    archive = (to / from_dir.name).with_suffix(".tar")

    with TarFile(name=archive, mode="w") as tar:
        for entry in from_dir.iterdir():
            tar.add(entry, arcname=entry.name)

    return archive


def pack_bundles_to_test() -> Path:
    tmp_path = Path(gettempdir(), f"test_bundles_{uuid.uuid4()}")
    tmp_path.mkdir()
    bundles_folder_path = Path("python/api_v2/tests/bundles")
    for bundle_path in bundles_folder_path.glob("*"):
        pack_bundle(bundle_path, tmp_path)
    return tmp_path


class TestBundleProcessing(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.already_existing_bundles = ["cluster_one.tar", "cluster_two.tar", "provider.tar"]
        self.packed_bundles = pack_bundles_to_test()

        self.empty_folder = Path(gettempdir(), f"empty_folder_{uuid.uuid4()}")
        self.empty_folder.mkdir()
        self.empty_folder_tar = pack_bundle(self.empty_folder, self.empty_folder)

        self.invalid_tar = Path(gettempdir(), f"invalid_tar_{uuid.uuid4()}")
        self.invalid_tar.touch()

        self.no_config_files = Path(gettempdir(), f"no_config_files_{uuid.uuid4()}")
        self.no_config_files.mkdir()
        (self.no_config_files / "not_a_config.txt").touch()
        self.no_config_files_tar = pack_bundle(self.no_config_files, self.no_config_files)

    def test_unpack_bundle_success(self) -> None:
        for bundle_path in self.packed_bundles.glob("*"):
            if bundle_path.name in self.already_existing_bundles:
                continue

            unpacked_files = unpack_bundle(bundle_path)

            self.assertIsNotNone(unpacked_files)

            for file_abs_path, file in unpacked_files:
                bundle_hash = get_hash_safe(path=bundle_path)
                extract_to = settings.BUNDLE_DIR / bundle_hash

                self.assertTrue((extract_to / file).is_file())
                self.assertTrue(file_abs_path)

                self.assertTrue(file_abs_path.suffix.endswith((".yaml", ".yml")))
                self.assertTrue(file.name.endswith((".yaml", ".yml")))

    def test_discovered_config_files_in_bundle_success(self) -> None:
        for bundle, expected_configs, are_there_subfolders, unexpected_files in [
            (
                "invalid_bundles.tar",
                [
                    Path("scripts_jinja_in_job/config.yaml"),
                    Path("plain_scripts_and_scripts_jinja/config.yaml"),
                ],
                True,
                [],
            ),
            ("cluster_config_host_group_upgrade.tar", [Path("config.yaml")], False, ["file.txt", "schema.yaml"]),
        ]:
            bundle_with_configs_path = list(self.packed_bundles.rglob(bundle)).pop()

            unpacked_files = unpack_bundle(bundle_with_configs_path)

            relative_configs = [rel_config[0] for rel_config in unpacked_files]
            abs_configs = [abs_config[1] for abs_config in unpacked_files]

            for config_yaml in expected_configs:
                self.assertIn(config_yaml, relative_configs)

                if are_there_subfolders:
                    abs_path_name = Path(f"{config_yaml.parent.name}/{config_yaml.name}")
                else:
                    abs_path_name = Path(f"{config_yaml.name}")

                self.assertEqual(config_yaml, abs_path_name)

            for abs_config in abs_configs:
                self.assertTrue(abs_config.is_absolute())

            for unexpected_file in unexpected_files:
                self.assertNotIn(unexpected_file, relative_configs)

    def tearDown(self) -> None:
        for temp_folder in [self.packed_bundles, self.empty_folder, self.no_config_files]:
            shutil.rmtree(temp_folder)
        os.remove(self.invalid_tar)
