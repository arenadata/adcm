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
import json
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping, TypeAlias

from api_v2.config.utils import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from cm.adcm_config.ansible import ansible_decrypt
from cm.api import add_hc, update_obj_config
from cm.inventory import get_inventory_data
from cm.models import (
    Action,
    ADCMEntity,
    ADCMModel,
    Cluster,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    ServiceComponent,
)
from cm.utils import deep_merge
from jinja2 import Template

from adcm.tests.base import BaseTestCase, BusinessLogicMixin

TemplatesData: TypeAlias = Mapping[tuple[str, ...], tuple[Path, Mapping[str, Any]]]
MappingEntry: TypeAlias = dict[Literal["host_id", "component_id", "service_id"], int]
Delta: TypeAlias = dict[Literal["add", "remove"], dict[str, dict[str, Host]]]


def decrypt_secrets(source: dict) -> dict:
    result = {}
    for key, value in source.items():
        if not isinstance(value, dict):
            if isinstance(value, list):
                result[key] = [entry if not isinstance(entry, dict) else decrypt_secrets(entry) for entry in value]
            else:
                result[key] = value
            continue

        if "__ansible_vault" in value:
            result[key] = ansible_decrypt(value["__ansible_vault"])
        else:
            result[key] = decrypt_secrets(value)

    return result


class BaseInventoryTestCase(BusinessLogicMixin, BaseTestCase):
    def setUp(self):
        super().setUp()

        self.maxDiff = None  # pylint: disable=invalid-name

        self.bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files" / "response_templates"

    @staticmethod
    def render_template(file: Path, context: dict) -> str:
        return Template(source=file.read_text(encoding="utf-8")).render(**context)

    def render_json_template(self, file: Path, context: dict) -> list | dict:
        return json.loads(self.render_template(file=file, context=context))

    def check_hosts_topology(self, data: Mapping[str, dict], expected: Mapping[str, list[str]]) -> None:
        errors = set(data.keys()).symmetric_difference(set(expected.keys()))
        self.assertSetEqual(errors, set())

        for group_name, host_names in expected.items():
            errors = set(data[group_name]["hosts"].keys()).symmetric_difference(set(host_names))
            self.assertSetEqual(
                errors, set(), msg=f"Host(s): '{', '.join(errors)}' should not be in the '{group_name}' group"
            )

    @staticmethod
    def set_hostcomponent(cluster: Cluster, entries: Iterable[tuple[Host, ServiceComponent]]) -> list[HostComponent]:
        return add_hc(
            cluster=cluster,
            hc_in=[
                {"host_id": host.pk, "component_id": component.pk, "service_id": component.service_id}
                for host, component in entries
            ],
        )

    @staticmethod
    def change_configuration(
        target: ADCMModel | GroupConfig,
        config_diff: dict,
        meta_diff: dict | None = None,
        preprocess_config: Callable[[dict], dict] = lambda x: x,
    ) -> ConfigLog:
        meta = meta_diff or {}

        target.refresh_from_db()
        current_config = ConfigLog.objects.get(id=target.config.current)

        new_config = update_obj_config(
            obj_conf=target.config,
            config=deep_merge(origin=preprocess_config(current_config.config), renovator=config_diff),
            attr=convert_adcm_meta_to_attr(
                deep_merge(origin=convert_attr_to_adcm_meta(current_config.attr), renovator=meta)
            ),
            description="",
        )

        return new_config

    def check_data_by_template(self, data: Mapping[str, dict], templates_data: TemplatesData) -> None:
        for key_chain, template_data in templates_data.items():
            template_path, kwargs = template_data

            expected_data = self.render_json_template(file=template_path, context=kwargs)
            actual_data = reduce(dict.get, key_chain, data)

            self.assertDictEqual(actual_data, expected_data)

    def get_action_on_host_expected_template_data_part(self, host: Host) -> TemplatesData:
        return {
            ("HOST", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": host.fqdn,
                    "adcm_hostid": host.pk,
                },
            ),
            ("HOST", "vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": host.provider.pk,
                    "host_prototype_id": host.prototype.pk,
                },
            ),
        }

    def assert_inventory(
        self, obj: ADCMEntity, action: Action, expected_topology: dict, expected_data: dict, delta: Delta | None = None
    ) -> None:
        actual_inventory = decrypt_secrets(
            source=get_inventory_data(obj=obj, action=action, delta=delta)["all"]["children"]
        )

        self.check_hosts_topology(data=actual_inventory, expected=expected_topology)
        self.check_data_by_template(data=actual_inventory, templates_data=expected_data)
