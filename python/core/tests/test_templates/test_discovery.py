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
from unittest import TestCase

from core.templates import (
    RendererEnv,
    TemplateFile,
    TemplateFileWithEntrypoint,
    TemplateRenderer,
    TemplateRendererJinja2,
    TemplateRendererPython,
)


class TestDiscoveryJinja2(TestCase):
    file_ext: str = "j2"

    def setUp(self) -> None:
        root = Path(__file__).parent / "files" / "discovery"

        self.bundle_1_root = root / "bundle_1"
        self.bundle_2_root = root / "bundle_2"

        self.root_file = Path(f"render.{self.file_ext}")
        self.inner_file = Path(f"inner/render.{self.file_ext}")

        super().setUp()

    def get_renderer(self, root: Path, file: Path) -> TemplateRenderer:
        return TemplateRendererJinja2(
            args=TemplateFile(path=file),
            env=RendererEnv(discovery_root=root),
        )

    def test_render_from_two_bundles_success(self):
        for bundle_root, template_file, expected_value in (
            # order of cases is semi-important, because it may break file resolution
            (self.bundle_1_root, self.root_file, "root-bundle-1"),
            (self.bundle_2_root, self.root_file, "root-bundle-2"),
            (self.bundle_2_root, self.inner_file, "inner-bundle-2"),
            (self.bundle_1_root, self.inner_file, "inner-bundle-1"),
        ):
            case_name = f"{bundle_root.name}-{template_file}-expect-{expected_value}"
            renderer = self.get_renderer(root=bundle_root, file=template_file)

            with self.subTest(case_name):
                render_result = renderer.render({})
                actual_value = render_result[0]["result"]

                self.assertEqual(actual_value, expected_value)


class TestDiscoveryPython(TestDiscoveryJinja2):
    file_ext = "py"

    def get_renderer(self, root: Path, file: Path) -> TemplateRenderer:
        return TemplateRendererPython(
            args=TemplateFileWithEntrypoint(path=file, entrypoint="main"),
            env=RendererEnv(discovery_root=root),
        )
