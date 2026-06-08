from pathlib import Path
from unittest import TestCase
import io
import shutil
import tarfile
import tempfile

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
    @classmethod
    def setUpClass(cls):
        cls.temp_root_obj = tempfile.TemporaryDirectory()
        cls.temp_root = Path(cls.temp_root_obj.name)
        cls.extract_dir = cls.temp_root / "extract"
        cls.extract_dir.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.temp_root_obj.cleanup()

    def setUp(self):
        for item in self.extract_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        self.tar_path = self.temp_root / "test.tar"
        if self.tar_path.exists():
            self.tar_path.unlink()

    def _create_tar(self, extra_members: dict[str, str]) -> Path:
        with tarfile.open(self.tar_path, "w") as tar:
            cfg_data = CONFIG_YAML.encode("utf-8")
            cfg_info = tarfile.TarInfo(name="config.yaml")
            cfg_info.size = len(cfg_data)
            tar.addfile(cfg_info, io.BytesIO(cfg_data))

            for name, content in extra_members.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return self.tar_path

    def test_untar_safe_normal_extra_file(self):
        archive = self._create_tar({"install.yaml": "# empty"})
        untar_safe(self.extract_dir, archive)

        self.assertTrue((self.extract_dir / "config.yaml").exists())
        self.assertTrue((self.extract_dir / "install.yaml").exists())

    def test_untar_safe_path_traversal_extra_file(self):
        archive = self._create_tar({"../../outside.txt": "malicious"})
        with self.assertRaises(BundleProcessingError) as ctx:
            untar_safe(self.extract_dir, archive)
        self.assertIn("Incorrect paths were found in the file", str(ctx.exception))
        outside_file = self.temp_root / "outside.txt"
        self.assertFalse(outside_file.exists())

    def test_untar_safe_symlink_pointing_outside(self):
        archive = self._create_tar({"target.txt": "data"})
        with tarfile.open(archive, "a") as tar:
            link_info = tarfile.TarInfo(name="evil_link")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "../../../outside"
            tar.addfile(link_info)
        with self.assertRaises(BundleProcessingError) as ctx:
            untar_safe(self.extract_dir, archive)
        self.assertIn("points outside", str(ctx.exception))
        self.assertFalse((self.extract_dir / "evil_link").exists())

    def test_untar_safe_symlink_pointing_inside(self):
        archive = self._create_tar({"target.txt": "secret"})
        with tarfile.open(archive, "a") as tar:
            link_info = tarfile.TarInfo(name="good_link")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "target.txt"
            tar.addfile(link_info)

        untar_safe(self.extract_dir, archive)

        self.assertTrue((self.extract_dir / "config.yaml").exists())
        self.assertTrue((self.extract_dir / "target.txt").exists())
        self.assertTrue((self.extract_dir / "good_link").exists())
        link_target = (self.extract_dir / "good_link").resolve()
        target_path = (self.extract_dir / "target.txt").resolve()
        self.assertEqual(link_target, target_path)
