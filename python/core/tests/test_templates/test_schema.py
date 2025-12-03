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

from unittest import TestCase

from pydantic import BaseModel, ValidationError

from core.templates import Jinja2Template, PythonTemplate, Template


class TestModel(BaseModel):
    value: Template


class TestTemplateSchema(TestCase):
    def test_adcm_7395_template_schema(self):
        with self.subTest("not dict (plain string) - fail"):
            with self.assertRaises(ValidationError):
                TestModel.model_validate({"value": "somefile.j2"})

        with self.subTest("PythonTemplate | Jinja2Template - success"):
            TestModel.model_validate(
                {
                    "value": PythonTemplate(
                        engine={"type": "python"}, file={"path": "some/path.py", "entrypoint": "main"}
                    )
                }
            )
            TestModel.model_validate(
                {"value": Jinja2Template(engine={"type": "jinja2"}, file={"path": "some/path.j2"})}
            )

        with self.subTest("correct dict - success"):
            TestModel.model_validate(
                {"value": {"engine": {"type": "python"}, "file": {"path": "some/path.py", "entrypoint": "main"}}}
            )
            TestModel.model_validate({"value": {"engine": {"type": "jinja2"}, "file": {"path": "some/path.j2"}}})
