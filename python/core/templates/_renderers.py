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

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path
from types import ModuleType
from typing import Any
import sys
import importlib

from jinja2 import Environment, FileSystemLoader, Template, TemplateError, select_autoescape
import yaml

from core.templates._errors import RenderError
from core.templates._types import RendererEnv, TemplateFile, TemplateFileWithEntrypoint, TemplateRenderer

# Renderers


@dataclass(slots=True)
class TemplateRendererPython(TemplateRenderer):
    args: TemplateFileWithEntrypoint

    env: RendererEnv

    @property
    def module_import_path(self) -> str:
        path_to_package = self.args.path.parent
        module_filename = self.args.path.stem

        cleaned_package_path = str(path_to_package).replace("/", ".").strip(".")

        return f"{cleaned_package_path}.{module_filename}".strip(".")

    def can_be_rendered(self) -> bool:
        try:
            with self._get_module(self.module_import_path) as module:
                self._get_entrypoint_from_module(module)
        except (ModuleNotFoundError, SyntaxError, AttributeError):
            return False

        return True

    def render(self, context: dict) -> Any:
        with reraise_as_render_error(), self._get_module(self.module_import_path) as module:
            func = self._get_entrypoint_from_module(module)
            return func(context)

    def _get_entrypoint_from_module(self, module: ModuleType) -> Callable:
        get_func = attrgetter(self.args.entrypoint)
        return get_func(module)

    @contextmanager
    def _get_module(self, import_path: str) -> Generator[ModuleType, None, None]:
        with add_to_path(self.env.discovery_root):
            module = importlib.import_module(import_path)
            # Need to force "reload" module to allow same named modules in different base directories
            # to be loaded correctly within one interpreter lifecycle
            importlib.reload(module)

            yield module


@dataclass(slots=True)
class TemplateRendererJinja2(TemplateRenderer):
    args: TemplateFile

    env: RendererEnv

    def can_be_rendered(self) -> bool:
        try:
            self._read_template()
        except (FileNotFoundError, TemplateError):
            return False

        return True

    def render(self, context: dict) -> Any:
        with reraise_as_render_error():
            template = self._read_template()
            yaml_content = str(template.render(**context))
            return yaml.load(stream=yaml_content, Loader=yaml.loader.SafeLoader)

    def _read_template(self) -> Template:
        j2_env = self._prepare_environment()
        template_name = str(self.args.path.name)
        return j2_env.get_template(template_name)

    def _prepare_environment(self) -> Environment:
        # Path discovery entries and order are important:
        # they affect both template discovering and path resolution in jinja2 runtime.
        bundle_root = self.env.discovery_root
        script_dir_within_bundle = bundle_root / self.args.path.parent
        paths_to_load = [str(script_dir_within_bundle), str(bundle_root)]

        loader = FileSystemLoader(paths_to_load)
        autoescape = select_autoescape(
            default_for_string=True, default=True, disabled_extensions=("j2", "jinja2", "yml", "yaml")
        )
        # Looks like typehints in jinja2.Environment doesn't work too well,
        # because in fact this function accepts callable, yet typehint says different.
        #
        # ruff have a problem with this one too, yet it's how it is working for now, can't change it
        return Environment(
            loader=loader,
            autoescape=autoescape,  # noqa: S701
        )


# Helpers


@contextmanager
def reraise_as_render_error():
    try:
        yield
    except Exception as e:  # noqa: BLE001
        message = f"Unexpected error occurred during template rendering: {e.__class__.__name__} {e}"
        raise RenderError(message) from e


@contextmanager
def add_to_path(p: Path):
    path = str(p.absolute())

    sys.path.insert(0, path)

    yield

    sys.path.pop(sys.path.index(path))
