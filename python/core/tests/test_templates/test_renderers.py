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

from abc import ABC, abstractmethod
from pathlib import Path
from unittest import TestCase

from core.templates._errors import RenderError
from core.templates._renderers import TemplateRendererJinja2, TemplateRendererPython
from core.templates._types import RendererEnv, TemplateFile, TemplateFileWithEntrypoint, TemplateRenderer


class _TemplateRendererBaseTest(ABC):
    files_dir: str
    file_ext: str

    partial_context_error: str

    def setUp(self) -> None:
        files_root_dir = Path(__file__).parent / "files" / self.files_dir

        self.environment = RendererEnv(discovery_root=files_root_dir)

        self.correct_file = Path(f"correct.{self.file_ext}")
        self.incorrect_file = Path(f"incorrect.{self.file_ext}")
        self.not_existing_file = Path(f"not-exist.{self.file_ext}")

    @abstractmethod
    def get_renderer(self, path: Path) -> TemplateRenderer:
        ...

    def test_correct_file_can_be_rendered_true(self):
        renderer = self.get_renderer(self.correct_file)
        result = renderer.can_be_rendered()
        self.assertTrue(result)

    def test_incorrect_file_can_be_rendered_false(self):
        renderer = self.get_renderer(self.incorrect_file)
        result = renderer.can_be_rendered()
        self.assertFalse(result)

    def test_not_existing_file_can_be_rendered_false(self):
        renderer = self.get_renderer(self.not_existing_file)
        result = renderer.can_be_rendered()
        self.assertFalse(result)

    def test_render_with_correct_context_success(self):
        context = {"plain_flag": True, "group": {"nested": "somestuff"}}
        expected_result = [
            {"know": "me", "value": context["plain_flag"]},
            {"know": "you", "value": context["group"]["nested"]},
        ]
        renderer = self.get_renderer(self.correct_file)

        result = renderer.render(context=context)

        self.assertEqual(result, expected_result)

    def test_render_with_partial_context_error(self):
        context = {"plain_flag": True}
        renderer = self.get_renderer(self.correct_file)

        with self.assertRaises(RenderError) as e:
            renderer.render(context=context)

        self.assertIn(self.partial_context_error, str(e.exception))


class TestJinja2TemplateRenderer(_TemplateRendererBaseTest, TestCase):
    files_dir = "jinja2"
    file_ext = "j2"

    partial_context_error = "'group' is undefined"

    def get_renderer(self, path: Path) -> TemplateRendererJinja2:
        return TemplateRendererJinja2(args=TemplateFile(path=path), env=self.environment)


class TestPythonTemplateRenderer(_TemplateRendererBaseTest, TestCase):
    files_dir = "python"
    file_ext = "py"

    partial_context_error = "KeyError 'group'"

    def get_renderer(self, path: Path, entrypoint: str = "generate_stuff") -> TemplateRendererPython:
        return TemplateRendererPython(
            args=TemplateFileWithEntrypoint(path=path, entrypoint=entrypoint), env=self.environment
        )

    def test_correct_file_incorrect_entrypoint_can_be_rendered_false(self):
        renderer = self.get_renderer(self.correct_file, entrypoint="notexist")
        result = renderer.can_be_rendered()
        self.assertFalse(result)

    def test_incorrect_entrypoint_error(self):
        renderer = self.get_renderer(self.correct_file, entrypoint="notexist")

        with self.assertRaises(RenderError) as e:
            renderer.render({})

        self.assertIn("module 'correct' has no attribute 'notexist'", str(e.exception))
