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

from functools import reduce
from json import loads
from pathlib import Path
from typing import Any, Iterable, Mapping, TypeAlias

from cm.adcm_config.ansible import ansible_decrypt
from cm.api import add_hc
from cm.inventory import get_inventory_data
from cm.models import (
    Action,
    ADCMEntity,
    Cluster,
    ConfigLog,
    Host,
    HostComponent,
    ServiceComponent,
)
from django.conf import settings
from jinja2 import Template

from adcm.tests.base import BaseTestCase, BusinessLogicMixin

TemplatesData: TypeAlias = Mapping[tuple[str, ...], tuple[Path, Mapping[str, Any]]]


def decrypt_secrets(source: dict) -> dict:
    result = {}
    for key, value in source.items():
        if not isinstance(value, dict):
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

    def check_hosts_topology(self, data: Mapping[str, dict], expected: Mapping[str, list[str]]) -> None:
        errors = set(data.keys()).symmetric_difference(set(expected.keys()))
        self.assertSetEqual(errors, set())

        for group_name, host_names in expected.items():
            errors = set(data[group_name]["hosts"].keys()).symmetric_difference(set(host_names))
            self.assertSetEqual(errors, set())

    @staticmethod
    def set_hostcomponent(cluster: Cluster, entries: Iterable[tuple[Host, ServiceComponent]]) -> list[HostComponent]:
        return add_hc(
            cluster=cluster,
            hc_in=[
                {"host_id": host.pk, "component_id": component.pk, "service_id": component.service_id}
                for host, component in entries
            ],
        )

    def check_data_by_template(self, data: Mapping[str, dict], templates_data: TemplatesData) -> None:
        for key_chain, template_data in templates_data.items():
            template_path, kwargs = template_data

            expected_data = loads(
                Template(source=template_path.read_text(encoding=settings.ENCODING_UTF_8)).render(kwargs), strict=False
            )
            actual_data = reduce(dict.get, key_chain, data)

            self.assertDictEqual(actual_data, expected_data)

    def get_action_on_host_expected_template_data_part(self, host: Host) -> TemplatesData:
        return {
            ("HOST", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": host.fqdn,
                    "adcm_hostid": host.pk,
                    "password": ConfigLog.objects.get(pk=host.config.current).config["password"],
                },
            ),
            ("HOST", "vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": host.provider.pk,
                    "password": ConfigLog.objects.get(pk=host.provider.config.current).config["password"],
                    "host_prototype_id": host.prototype.pk,
                },
            ),
        }

    def assert_inventory(self, obj: ADCMEntity, action: Action, expected_topology: dict, expected_data: dict):
        actual_inventory = get_inventory_data(obj=obj, action=action)["all"]["children"]

        self.check_hosts_topology(data=actual_inventory, expected=expected_topology)
        self.check_data_by_template(data=actual_inventory, templates_data=expected_data)
