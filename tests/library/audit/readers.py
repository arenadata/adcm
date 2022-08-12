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

"""Audit log scenarios readers"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Literal, NamedTuple, Optional, Union

import allure
import jsonschema
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


@dataclass(frozen=True)
class _ProcessorConfig:
    process_type: Literal['exact', 'sequence', 'presence'] = 'sequence'
    start_from_first: Literal['record', 'matched'] = 'matched'


@dataclass(frozen=True)
class _ResolveDefaults:
    result: Literal['success', 'fail', 'denied'] = 'success'
    username: str = 'admin'


class ParsedAuditLog(NamedTuple):
    """Information about expected audit log records parsed from file"""

    defaults: _ResolveDefaults
    settings: _ProcessorConfig
    operations: Dict[str, dict]


_TemplateContext = Optional[Dict[str, Union[str, int]]]


@lru_cache
def _get_schema() -> dict:
    with (Path(__file__).parent / 'audit_log_schema.json').open() as schema:
        return json.load(schema)


class YAMLReader:
    """
    Reader of expected audit logs from `.yaml` file.
    Aim it to the directory with audit log scenarios
        and then pass name of the scenario (with extension)
        alongside with the jinja2 context
    """

    def __init__(self, directory: os.PathLike):
        self._directory = directory
        self._template_env = Environment(loader=FileSystemLoader(directory), undefined=StrictUndefined, autoescape=True)

    def prepare_parser_of(self, filename: str) -> Callable[[_TemplateContext], ParsedAuditLog]:
        """
        Prepare function to pass only context to template file, so it can be called without providing filename
        """
        return lambda ctx: self.parse(filename, ctx)

    def parse(self, filename: str, context: _TemplateContext = None) -> ParsedAuditLog:
        """
        Format file with audit log scenario with given context
        and parse it to extract valuable information about audited operations
            and how they should be checked
        """
        context = context or {}
        data = self._read(filename, context)
        return ParsedAuditLog(
            defaults=_ResolveDefaults(**data.get('defaults', {})),
            operations=data.get('operations'),
            settings=_ProcessorConfig(**{k.replace('-', '_'): v for k, v in data.get('settings', {}).items()}),
        )

    def _read(self, filename: str, context: Dict[str, Union[str, int]]) -> dict:
        rendered_file_content = self._template_env.get_template(filename).render(**context)
        data = yaml.safe_load(rendered_file_content)
        jsonschema.validate(data, _get_schema())
        allure.attach(
            json.dumps(data, indent=2), name='Audit Log scenario', attachment_type=allure.attachment_type.JSON
        )
        return data
