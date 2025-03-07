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

from pydantic import ValidationError
import yaml

from core.bundle_alt.schema import TYPE_SCHEMA_MAP


class TestBundleSchema(TestCase):
    """Here we're testing schemas retrieval on minimal definitions"""

    @staticmethod
    def validate_schema(entries: list[dict] | dict) -> list[dict]:
        schemas = []

        if isinstance(entries, dict):
            entries = [entries]

        for item in entries:
            schema = TYPE_SCHEMA_MAP[item["type"]].model_validate(item, strict=True)
            schemas.append(schema.model_dump())

        return schemas

    def test_cluster(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              flag_autogeneration:
                enable_outdated_config: true
              import:
                service:
                  versions:
                    min: 1
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            self.assertEqual(len(schemas), 1)

            expected = {
                "type": "cluster",
                "name": "some_cluster",
                "version": 12,
                "adcm_min_version": None,
                "display_name": None,
                "description": None,
                "edition": None,
                "license": None,
                "config": None,
                "actions": None,
                "venv": None,
                "flag_autogeneration": {"enable_outdated_config": True},
                "upgrade": None,
                "imports": {
                    "service": {
                        "versions": {"min": 1, "max": None, "min_strict": None, "max_strict": None},
                        "required": None,
                        "multibind": None,
                        "default": None,
                    }
                },
                "export": None,
                "config_group_customization": None,
                "allow_maintenance_mode": None,
            }
            self.assertDictEqual(schemas[0], expected)

        with self.subTest("With extra field"):
            # cluster
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              extra: field
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(entries=raw)

            # flag_autogeneration
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              flag_autogeneration:
                enable_outdated_config: true
                second_flag: false
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(entries=raw)

            # import
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              import:
                service:
                  versions:
                    min: 1
                  import_property: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(entries=raw)

    def test_service(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              requires:
                - service: s1
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            self.assertEqual(len(schemas), 2)

            _, service_schema = schemas
            expected_service = {
                "type": "service",
                "name": "some_service",
                "version": 11,
                "adcm_min_version": None,
                "display_name": None,
                "description": None,
                "edition": None,
                "license": None,
                "config": None,
                "actions": None,
                "venv": None,
                "flag_autogeneration": None,
                "imports": None,
                "export": None,
                "shared": None,
                "components": None,
                "required": None,
                "requires": [{"service": "s1", "component": None}],
                "monitoring": None,
                "config_group_customization": None,
            }
            self.assertDictEqual(service_schema, expected_service)

        with self.subTest("With extra field"):
            # service
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              attr: not valid
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # requires
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              requires:
                - service: s1
                  cluster: cluster
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_component(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)

            _, service_schema = schemas
            self.assertIsNone(service_schema["components"])

            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
                some_component:
                  bound_to:
                    service: s1
                    component: c1
                  requires:
                    - service: s2
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)

            _, service_schema = schemas
            expected_components = {
                "some_component": {
                    "display_name": None,
                    "description": None,
                    "monitoring": None,
                    "constraint": None,
                    "bound_to": {"service": "s1", "component": "c1"},
                    "params": None,
                    "requires": [{"service": "s2", "component": None}],
                    "config": None,
                    "actions": None,
                    "config_group_customization": None,
                    "flag_autogeneration": None,
                    "venv": None,
                }
            }
            self.assertDictEqual(service_schema["components"], expected_components)

            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
                some_component:
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)

            _, service_schema = schemas
            expected_components["some_component"].update({"bound_to": None, "requires": None})
            self.assertDictEqual(service_schema["components"], expected_components)

        with self.subTest("With extra field"):
            # component
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
                some_component:
                  display_name: Some component
                  attribute: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # bound_to
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
                some_component:
                  bound_to:
                    service: s1
                    component: c1
                    extra: field
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # requires
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12

            - type: service
              name: some_service
              version: 11
              components:
                some_component:
                  requires:
                    - service: s2
                      field: forbidden
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_provider(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: provider
              name: some_provider
              version: 8
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            self.assertEqual(len(schemas), 1)

            expected_provider = {
                "type": "provider",
                "name": "some_provider",
                "version": 8,
                "adcm_min_version": None,
                "display_name": None,
                "description": None,
                "edition": None,
                "license": None,
                "config": None,
                "actions": None,
                "venv": None,
                "flag_autogeneration": None,
                "upgrade": None,
                "config_group_customization": None,
            }
            self.assertDictEqual(schemas[0], expected_provider)

        with self.subTest("With extra field"):
            yaml_schema = """
            - type: provider
              name: some_provider
              version: 8
              new: field
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_host(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: provider
              name: some_provider
              version: 8

            - type: host
              name: some_host
              version: 9
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            self.assertEqual(len(schemas), 2)

            _, host_schema = schemas
            expected_host = {
                "name": "some_host",
                "type": "host",
                "version": 9,
                "actions": None,
                "adcm_min_version": None,
                "config": None,
                "description": None,
                "display_name": None,
                "edition": None,
                "flag_autogeneration": None,
                "license": None,
                "venv": None,
            }
            self.assertDictEqual(host_schema, expected_host)

        with self.subTest("With extra field"):
            yaml_schema = """
            - type: provider
              name: some_provider
              version: 8

            - type: host
              name: some_host
              version: 9
              newfield: somevalue
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_adcm(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: adcm
              name: some_adcm
              version: 3
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            self.assertEqual(len(schemas), 1)

            expected_adcm = {
                "name": "some_adcm",
                "type": "adcm",
                "version": 3,
                "actions": None,
                "adcm_min_version": None,
                "config": None,
                "description": None,
                "display_name": None,
                "edition": None,
                "flag_autogeneration": None,
                "license": None,
                "upgrade": None,
                "venv": None,
            }
            self.assertDictEqual(schemas[0], expected_adcm)

        with self.subTest("With extra field"):
            yaml_schema = """
            - type: adcm
              name: some_adcm
              version: 3
              adcm_property: adcm_value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_upgrade(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 2
                  states:
                    available: any
                    on_success: upgraded
                    on_fail: failed
                  scripts:
                    - name: script_1
                      script: script.yaml
                      script_type: ansible
                  masking:
                    state:
                      unavailable: any
                    multi_state:
                      available: any
                  hc_acl:
                    - component: component_1
                      action: add
                      service: service_1
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            upgrades = schemas[0]["upgrade"]
            self.assertEqual(len(upgrades), 1)

            expected_upgrade = {
                "name": "some_upgrade",
                "versions": {"min": 1, "max": 2, "min_strict": None, "max_strict": None},
                "states": {"available": "any", "on_success": "upgraded", "on_fail": "failed"},
                "scripts": [
                    {
                        "name": "script_1",
                        "script": "script.yaml",
                        "script_type": "ansible",
                        "display_name": None,
                        "params": None,
                        "on_fail": None,
                    }
                ],
                "masking": {"state": {"unavailable": "any"}, "multi_state": {"available": "any"}},
                "hc_acl": [{"component": "component_1", "action": "add", "service": "service_1"}],
                "display_name": None,
                "description": None,
                "from_edition": None,
                "on_fail": None,
                "on_success": None,
                "venv": None,
                "ui_options": None,
                "config": None,
            }
            self.assertDictEqual(upgrades[0], expected_upgrade)

            yaml_schema = """
            - type: provider
              name: some_provider
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                    min: 8
                    max: 12
            """
            raw = yaml.safe_load(yaml_schema)
            schemas = self.validate_schema(raw)
            upgrades = schemas[0]["upgrade"]
            self.assertEqual(len(upgrades), 1)

            expected_upgrade = {
                "name": "some_upgrade",
                "versions": {"min": 8, "max": 12, "min_strict": None, "max_strict": None},
                "display_name": None,
                "description": None,
                "states": None,
                "from_edition": None,
                "scripts": None,
                "masking": None,
                "on_fail": None,
                "on_success": None,
                "venv": None,
                "ui_options": None,
                "config": None,
            }
            self.assertDictEqual(upgrades[0], expected_upgrade)

        with self.subTest("With extra field"):
            # upgrade
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  upgrade_property: 123
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # versions
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                      maximum_version: 12
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # states
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  states:
                    available: any
                    on_success: upgraded
                    on_fail: failed
                    some_field: some_value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # scripts
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  scripts:
                    - name: script_1
                      script: script.yaml
                      script_type: ansible
                      abra: cadabra
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # masking
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  masking:
                    state:
                      unavailable: any
                    multi_state:
                      available: any
                    masking_attr: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # masking.state
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  masking:
                    state:
                      unavailable: any
                      field: value
                    multi_state:
                      available: any
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # masking.multi_state
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 4
                  masking:
                    state:
                      unavailable: any
                    multi_state:
                      available: any
                      field: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # hc_acl
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              upgrade:
                - name: some_upgrade
                  versions:
                      min: 1
                      max: 5
                  hc_acl:
                    - component: component_1
                      action: add
                      service: service_1
                      field: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_actions(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                job:
                  type: job
                  script_type: ansible
                  script: path/to/script.yaml
                task_plain:
                  type: task
                  scripts:
                    - name: job_1
                      script_type: python
                      script: path/to/script.py
                task_jinja:
                  type: task
                  scripts_jinja: path/to/script_jinja.j2
            """
            raw = yaml.safe_load(yaml_schema)
            actions = self.validate_schema(raw)[0]["actions"]

            expected_actions = {
                "job": {
                    "type": "job",
                    "script_type": "ansible",
                    "script": "path/to/script.yaml",
                    "display_name": None,
                    "description": None,
                    "params": None,
                    "ui_options": None,
                    "allow_to_terminate": None,
                    "partial_execution": None,
                    "host_action": None,
                    "allow_for_action_host_group": None,
                    "log_files": None,
                    "states": None,
                    "masking": None,
                    "on_fail": None,
                    "on_success": None,
                    "hc_acl": None,
                    "venv": None,
                    "allow_in_maintenance_mode": None,
                    "config": None,
                    "config_jinja": None,
                },
                "task_plain": {
                    "type": "task",
                    "scripts": [
                        {
                            "name": "job_1",
                            "script": "path/to/script.py",
                            "script_type": "python",
                            "display_name": None,
                            "params": None,
                            "on_fail": None,
                            "allow_to_terminate": None,
                        }
                    ],
                    "display_name": None,
                    "description": None,
                    "params": None,
                    "ui_options": None,
                    "allow_to_terminate": None,
                    "partial_execution": None,
                    "host_action": None,
                    "allow_for_action_host_group": None,
                    "log_files": None,
                    "states": None,
                    "masking": None,
                    "on_fail": None,
                    "on_success": None,
                    "hc_acl": None,
                    "venv": None,
                    "allow_in_maintenance_mode": None,
                    "config": None,
                    "config_jinja": None,
                },
                "task_jinja": {
                    "type": "task",
                    "scripts_jinja": "path/to/script_jinja.j2",
                    "display_name": None,
                    "description": None,
                    "params": None,
                    "ui_options": None,
                    "allow_to_terminate": None,
                    "partial_execution": None,
                    "host_action": None,
                    "allow_for_action_host_group": None,
                    "log_files": None,
                    "states": None,
                    "masking": None,
                    "on_fail": None,
                    "on_success": None,
                    "hc_acl": None,
                    "venv": None,
                    "allow_in_maintenance_mode": None,
                    "config": None,
                    "config_jinja": None,
                },
            }
            self.assertDictEqual(actions, expected_actions)

        with self.subTest("With extra field"):
            # job
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                job:
                  type: job
                  script_type: ansible
                  script: path/to/script.yaml
                  venv: 2.9
                  not_venv: 3.0
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # task
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                task_plain:
                  type: task
                  scripts:
                    - name: job_1
                      script_type: python
                      script: path/to/script.py
                  task_field: value
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # scripts
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                task_plain:
                  type: task
                  scripts:
                    - name: job_1
                      script_type: python
                      script: path/to/script.py
                      script_version: 3
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # on_fail
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                task_plain:
                  type: task
                  scripts:
                    - name: job_1
                      script_type: python
                      script: path/to/script.py
                      on_fail:
                        state: failed
                        extra: field
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            # multi_state
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 3
              actions:
                task_plain:
                  type: task
                  scripts:
                    - name: job_1
                      script_type: python
                      script: path/to/script.py
                      on_fail:
                        multi_state:
                          set:
                            - some state
                          attr: val
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

    def test_config(self):
        with self.subTest("Success case"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              config:
                - name: bool_field
                  type: boolean
                - name: int_field
                  type: integer
                - name: float_field
                  type: float
                - name: file_field
                  type: file
                - name: secretfile_field
                  type: secretfile
                - name: string_field
                  type: string
                - name: password_field
                  type: password
                - name: secrettext_field
                  type: secrettext
                - name: text_field
                  type: text
                - name: list_field
                  type: list
                - name: map_field
                  type: map
                - name: secretmap_field
                  type: secretmap
                - name: structure_field
                  type: structure
                  yspec: path/to/yspec.yaml
                - name: json_field
                  type: json
                - name: option_field
                  type: option
                  option:
                    some_key: some_value
                    some_key2: some_value2
                - name: variant_field
                  type: variant
                  source:
                    type: builtin
                    name: host
                    args:
                      predicate: and
                      args:
                        - predicate: in_service
                          args:
                            service: first_service
                        - predicate: or
                          args:
                            - predicate: in_component
                              args:
                                service: first_service
                                component: first_1
                            - predicate: in_cluster
                              args:
                - name: group_field
                  type: group
                  subs:
                    - name: bool_field
                      type: boolean
                    - name: int_field
                      type: integer
                    - name: float_field
                      type: float
                    - name: file_field
                      type: file
                    - name: secretfile_field
                      type: secretfile
                    - name: string_field
                      type: string
                    - name: password_field
                      type: password
                    - name: secrettext_field
                      type: secrettext
                    - name: text_field
                      type: text
                    - name: list_field
                      type: list
                    - name: map_field
                      type: map
                    - name: secretmap_field
                      type: secretmap
                    - name: structure_field
                      type: structure
                      yspec: path/to/yspec.yaml
                    - name: json_field
                      type: json
                    - name: option_field
                      type: option
                      option:
                        some_key: some_value
                        some_key2: some_value2
                    - name: variant_field
                      type: variant
                      source:
                        type: builtin
                        name: host
                        args:
                          predicate: and
                          args:
                            - predicate: in_service
                              args:
                                service: first_service
                            - predicate: or
                              args:
                                - predicate: in_component
                                  args:
                                    service: first_service
                                    component: first_1
                                - predicate: in_cluster
                                  args:
            """
            raw = yaml.safe_load(yaml_schema)
            config = self.validate_schema(raw)[0]["config"]

            common_config_fields = {
                "read_only": None,
                "writable": None,
                "required": None,
                "display_name": None,
                "description": None,
                "ui_options": None,
                "group_customization": None,
                "default": None,
            }
            expected_config = [
                {"type": "boolean", "name": "bool_field", **common_config_fields},
                {"type": "integer", "name": "int_field", "min": None, "max": None, **common_config_fields},
                {"type": "float", "name": "float_field", "min": None, "max": None, **common_config_fields},
                {"type": "file", "name": "file_field", **common_config_fields},
                {"type": "secretfile", "name": "secretfile_field", **common_config_fields},
                {"type": "string", "name": "string_field", "pattern": None, **common_config_fields},
                {"type": "password", "name": "password_field", "pattern": None, **common_config_fields},
                {"type": "secrettext", "name": "secrettext_field", "pattern": None, **common_config_fields},
                {"type": "text", "name": "text_field", "pattern": None, **common_config_fields},
                {"type": "list", "name": "list_field", **common_config_fields},
                {"type": "map", "name": "map_field", **common_config_fields},
                {"type": "secretmap", "name": "secretmap_field", **common_config_fields},
                {"type": "structure", "name": "structure_field", "yspec": "path/to/yspec.yaml", **common_config_fields},
                {"type": "json", "name": "json_field", **common_config_fields},
                {
                    "type": "option",
                    "name": "option_field",
                    "option": {"some_key": "some_value", "some_key2": "some_value2"},
                    **common_config_fields,
                },
                {
                    "type": "variant",
                    "name": "variant_field",
                    "source": {
                        "type": "builtin",
                        "strict": None,
                        "name": "host",
                        "args": {
                            "predicate": "and",
                            "args": [
                                {"predicate": "in_service", "args": {"service": "first_service"}},
                                {
                                    "predicate": "or",
                                    "args": [
                                        {
                                            "predicate": "in_component",
                                            "args": {"service": "first_service", "component": "first_1"},
                                        },
                                        {"predicate": "in_cluster", "args": None},
                                    ],
                                },
                            ],
                        },
                    },
                    **common_config_fields,
                },
                {
                    "type": "group",
                    "name": "group_field",
                    "read_only": None,
                    "writable": None,
                    "required": None,
                    "display_name": None,
                    "description": None,
                    "ui_options": None,
                    "group_customization": None,
                    "subs": [
                        {"type": "boolean", "name": "bool_field", **common_config_fields},
                        {"type": "integer", "name": "int_field", "min": None, "max": None, **common_config_fields},
                        {"type": "float", "name": "float_field", "min": None, "max": None, **common_config_fields},
                        {"type": "file", "name": "file_field", **common_config_fields},
                        {"type": "secretfile", "name": "secretfile_field", **common_config_fields},
                        {"type": "string", "name": "string_field", "pattern": None, **common_config_fields},
                        {"type": "password", "name": "password_field", "pattern": None, **common_config_fields},
                        {"type": "secrettext", "name": "secrettext_field", "pattern": None, **common_config_fields},
                        {"type": "text", "name": "text_field", "pattern": None, **common_config_fields},
                        {"type": "list", "name": "list_field", **common_config_fields},
                        {"type": "map", "name": "map_field", **common_config_fields},
                        {"type": "secretmap", "name": "secretmap_field", **common_config_fields},
                        {
                            "type": "structure",
                            "name": "structure_field",
                            "yspec": "path/to/yspec.yaml",
                            **common_config_fields,
                        },
                        {"type": "json", "name": "json_field", **common_config_fields},
                        {
                            "type": "option",
                            "name": "option_field",
                            "option": {"some_key": "some_value", "some_key2": "some_value2"},
                            **common_config_fields,
                        },
                        {
                            "type": "variant",
                            "name": "variant_field",
                            "source": {
                                "type": "builtin",
                                "strict": None,
                                "name": "host",
                                "args": {
                                    "predicate": "and",
                                    "args": [
                                        {"predicate": "in_service", "args": {"service": "first_service"}},
                                        {
                                            "predicate": "or",
                                            "args": [
                                                {
                                                    "predicate": "in_component",
                                                    "args": {"service": "first_service", "component": "first_1"},
                                                },
                                                {"predicate": "in_cluster", "args": None},
                                            ],
                                        },
                                    ],
                                },
                            },
                            **common_config_fields,
                        },
                    ],
                    "activatable": None,
                    "active": None,
                },
            ]
            self.assertListEqual(config, expected_config)

        with self.subTest("With extra field"):
            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              config:
                - name: bool_field
                  type: boolean
                  required: true
                  flag: false
            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)

            yaml_schema = """
            - type: cluster
              name: some_cluster
              version: 12
              config:
                - name: group_field
                  type: group
                  activatable: true
                  active: true
                  subs:
                    - name: int_field
                      type: integer
                      min: 3
                      maximum_value: 8

            """
            raw = yaml.safe_load(yaml_schema)
            with self.assertRaises(ValidationError):
                self.validate_schema(raw)
