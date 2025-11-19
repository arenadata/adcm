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

from importlib import import_module
from pathlib import Path
from unittest import TestCase
import json

from core.config._spec.jsonschema import spec_to_jsonschema


def enforce_regular_dict(d: dict) -> dict:
    return {k: enforce_regular_dict(v) if isinstance(v, dict) else v for k, v in d.items()}


class TestJsonSchemaGeneration(TestCase):
    maxDiff = None

    def test_cases(self):
        # For now can't parse something like "config.yaml",
        # because direct conversion of bundle format ot FullSpec not supported
        import_template = "core.tests.test_config.files.jsonschema.cases.{dir_}.schema"
        cases_dir = Path(__file__).parent / "files" / "jsonschema" / "cases"

        for case_dir in cases_dir.iterdir():
            with self.subTest(case_dir.name):
                builder_module_name = import_template.format(dir_=case_dir.name)
                builder_module = import_module(builder_module_name)

                spec, defaults = builder_module.build()

                expected_schema = json.loads((case_dir / "schema.json").read_text())

                actual_schema = spec_to_jsonschema(
                    spec=spec,
                    defaults=defaults,
                    owner_state="created",
                    is_group_config=False,
                    resolve_variant=lambda _: ("v1", "v2"),
                )

                actual_schema_as_regular_dict = enforce_regular_dict(actual_schema)

                self.assertDictEqual(
                    actual_schema_as_regular_dict,
                    expected_schema,
                    f"\n=== ACTUAL ===\n{json.dumps(actual_schema_as_regular_dict, indent=4)}",
                )
