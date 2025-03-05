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
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, TypeAlias
import json

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from core.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.cluster.types import HostComponentEntry
from core.types import CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from jinja2 import Template

from cm.adcm_config.ansible import ansible_decrypt
from cm.converters import model_name_to_core_type
from cm.models import (
    Action,
    ADCMEntity,
    ADCMModel,
    ConfigHostGroup,
    Host,
    MaintenanceMode,
)
from cm.services.cluster import retrieve_cluster_topology
from cm.services.job._utils import construct_delta_for_task
from cm.services.job.inventory import get_inventory_data
from cm.services.job.types import TaskMappingDelta

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

        self.maxDiff = None

        self.bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files" / "response_templates"

    @staticmethod
    def render_template(file: Path, context: dict) -> str:
        return Template(source=file.read_text(encoding="utf-8")).render(**context)

    def render_json_template(self, file: Path, context: dict) -> list | dict:
        return json.loads(self.render_template(file=file, context=context))

    def check_hosts_topology(self, data: Mapping[str, dict], expected: Mapping[str, list[str]]) -> None:
        self.assertSetEqual(set(data.keys()), set(expected.keys()))

        for group_name, host_names in expected.items():
            self.assertSetEqual(set(data[group_name]["hosts"].keys()), set(host_names))

    def check_data_by_template(self, data: Mapping[str, dict], templates_data: TemplatesData) -> None:
        for key_chain, template_data in templates_data.items():
            template_path, kwargs = template_data

            full_key_chain = ("all", *key_chain)

            expected_data = self.render_json_template(file=template_path, context=kwargs)
            actual_data = reduce(dict.get, full_key_chain, data)

            self.assertDictEqual(actual_data, expected_data)

    def assert_inventory(
        self,
        obj: ADCMEntity,
        action: Action,
        expected_topology: dict,
        expected_data: dict,
        delta: TaskMappingDelta | None = None,
    ) -> None:
        target = CoreObjectDescriptor(id=obj.id, type=model_name_to_core_type(obj.__class__.__name__))
        actual_inventory = decrypt_secrets(
            source=get_inventory_data(target=target, is_host_action=action.host_action, delta=delta)
        )

        self.check_hosts_topology(data=actual_inventory["all"]["children"], expected=expected_topology)
        self.check_data_by_template(data=actual_inventory, templates_data=expected_data)

    @staticmethod
    def add_config_host_group(parent: ADCMModel, hosts: Iterable[Host]) -> ConfigHostGroup:
        host_group = ConfigHostGroup.objects.create(
            object_type=ContentType.objects.get_for_model(model=parent),
            object_id=parent.pk,
            name=f"Group for {parent.__class__.__name__} {parent.pk}",
        )
        host_group.hosts.set(hosts)
        return host_group

    @staticmethod
    def get_mapping_delta_for_hc_acl(cluster, new_mapping: list[MappingEntry]) -> TaskMappingDelta:
        topology = retrieve_cluster_topology(cluster_id=cluster.id)
        new_topology = create_topology_with_new_mapping(
            topology=topology,
            new_mapping=(
                HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                for entry in new_mapping
            ),
        )

        return construct_delta_for_task(
            topology=new_topology,
            host_difference=find_hosts_difference(new_topology=new_topology, old_topology=topology),
        )

    @staticmethod
    def get_maintenance_mode_for_render(maintenance_mode: MaintenanceMode) -> str:
        if maintenance_mode == MaintenanceMode.ON:
            return "true"

        return "false"
