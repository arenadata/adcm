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

from jinja2 import Template, UndefinedError
import yaml


class TemplateBuilder:
    __slots__ = ("_template_path", "_error", "_context", "_data")

    def __init__(self, template_path: Path | str, context: dict, error: Exception | None = None):
        self._template_path = Path(template_path)
        self._context = context
        self._error = error
        self._data = None

    @property
    def data(self):
        if self._data is not None:
            return self._data

        try:
            template = Template(source=self._template_path.read_text(encoding="utf-8"))
            data_yaml = template.render(**self._context)
            data = yaml.load(stream=data_yaml, Loader=yaml.loader.SafeLoader)
        except (yaml.reader.ReaderError, UndefinedError, FileNotFoundError, TypeError) as e:
            if self._error is not None:
                raise self._error from e
            raise

        self._data = data

        return data
