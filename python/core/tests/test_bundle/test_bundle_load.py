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

import io
import shutil
import tarfile
from pathlib import Path
from unittest import TestCase

from core.legacy.bundle_alt.bundle_load import untar_safe
from core.legacy.bundle_alt.errors import BundleProcessingError

CONFIG_YAML = """\
- name: ADBG
  type: cluster
  version: 1.0
  venv: "2.16"
  config: []
  actions:
    install:
      scripts:
        - name: install
          script: ./install.yaml
          script_type: ansible
  contract_version: '2.1'
"""


class TestUntarSafe(TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(__file__).parent / "temp_test_untar"
        self.temp_dir.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_tar(self, extra_members: dict[str, str]) -> Path:
        tar_path = self.temp_dir / "test.tar"
        with tarfile.open(tar_path, "w") as tar:
            cfg_data = CONFIG_YAML.encode("utf-8")
            cfg_info = tarfile.TarInfo(name="config.yaml")
            cfg_info.size = len(cfg_data)
            tar.addfile(cfg_info, io.BytesIO(cfg_data))

            for name, content in extra_members.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return tar_path

    def test_untar_safe_normal_extra_file(self):
        archive = self._create_tar({"install.yaml": "# empty"})
        extract_dir = self.temp_dir / "extract"
        extract_dir.mkdir()

        untar_safe(extract_dir, archive)

        self.assertTrue((extract_dir / "config.yaml").exists())
        self.assertTrue((extract_dir / "install.yaml").exists())

    def test_untar_safe_path_traversal_extra_file(self):
        archive = self._create_tar({"../../outside.txt": "malicious"})
        extract_dir = self.temp_dir / "extract"
        extract_dir.mkdir()

        with self.assertRaises(BundleProcessingError) as ctx:
            untar_safe(extract_dir, archive)

        self.assertIn("TarSlip detected", str(ctx.exception))
        outside_file = self.temp_dir / "outside.txt"
        self.assertFalse(outside_file.exists())

    def test_untar_safe_symlink_pointing_outside(self):
        archive = self._create_tar({"target.txt": "data"})
        with tarfile.open(archive, "a") as tar:
            link_info = tarfile.TarInfo(name="evil_link")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "../../../outside"
            tar.addfile(link_info)

        extract_dir = self.temp_dir / "extract"
        extract_dir.mkdir()

        with self.assertRaises(BundleProcessingError) as ctx:
            untar_safe(extract_dir, archive)

        self.assertIn("points outside", str(ctx.exception))
        self.assertFalse((extract_dir / "evil_link").exists())

    def test_untar_safe_symlink_pointing_inside(self):
        archive = self._create_tar({"target.txt": "secret"})
        with tarfile.open(archive, "a") as tar:
            link_info = tarfile.TarInfo(name="good_link")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "target.txt"
            tar.addfile(link_info)

        extract_dir = self.temp_dir / "extract"
        extract_dir.mkdir()

        untar_safe(extract_dir, archive)

        self.assertTrue((extract_dir / "config.yaml").exists())
        self.assertTrue((extract_dir / "target.txt").exists())
        self.assertTrue((extract_dir / "good_link").exists())
        # Проверяем, что симлинк ведёт на target.txt
        link_target = (extract_dir / "good_link").resolve()
        target_path = (extract_dir / "target.txt").resolve()
        self.assertEqual(link_target, target_path)
