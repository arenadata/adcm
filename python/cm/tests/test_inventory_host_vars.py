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

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from cm.api import update_obj_config
from cm.inventory import get_host_vars
from cm.models import ConfigLog, GroupConfig, ObjectConfig
from cm.tests.utils import (
    gen_bundle,
    gen_cluster,
    gen_component,
    gen_config,
    gen_host,
    gen_host_component,
    gen_prototype,
    gen_prototype_config,
    gen_provider,
    gen_service,
)


class TestInventory(TestCase):
    # pylint: disable=too-many-locals
    # TODO: refactor this file and merge it with cm/tests/test_inventory after audit merge

    def setUp(self):
        object_config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=object_config, config={"some_string": "some_string"})

        cluster_bundle = gen_bundle()
        cluster_pt = gen_prototype(cluster_bundle, "cluster", "cluster")
        service_pt_1 = gen_prototype(cluster_bundle, "service", "service_1")
        service_pt_2 = gen_prototype(cluster_bundle, "service", "service_2")
        component_pt_11 = gen_prototype(cluster_bundle, "component", "component_11")
        component_pt_12 = gen_prototype(cluster_bundle, "component", "component_12")
        component_pt_21 = gen_prototype(cluster_bundle, "component", "component_21")

        prototypes = [
            cluster_pt,
            service_pt_1,
            service_pt_2,
            component_pt_11,
            component_pt_12,
            component_pt_21,
        ]
        for proto in prototypes:
            gen_prototype_config(
                prototype=proto,
                name="some_string",
                field_type="string",
                group_customization=True,
            )

        self.cluster = gen_cluster(prototype=cluster_pt, config=object_config, name="cluster")
        self.service_1 = gen_service(
            self.cluster,
            prototype=service_pt_1,
            config=gen_config({"some_string": "some_string"}),
        )
        self.service_2 = gen_service(
            self.cluster,
            prototype=service_pt_2,
            config=gen_config({"some_string": "some_string"}),
        )
        self.component_11 = gen_component(
            self.service_1,
            prototype=component_pt_11,
            config=gen_config({"some_string": "some_string"}),
        )
        self.component_12 = gen_component(
            self.service_1,
            prototype=component_pt_12,
            config=gen_config({"some_string": "some_string"}),
        )
        self.component_21 = gen_component(
            self.service_2,
            prototype=component_pt_21,
            config=gen_config({"some_string": "some_string"}),
        )

        provider_bundle = gen_bundle()

        provider_pt = gen_prototype(provider_bundle, "provider")
        host_pt = gen_prototype(provider_bundle, "host")

        provider = gen_provider(prototype=provider_pt)
        self.host = gen_host(provider, prototype=host_pt, cluster=self.cluster)
        gen_host_component(self.component_11, self.host)
        gen_host_component(self.component_12, self.host)
        gen_host_component(self.component_21, self.host)

        groups = []
        groups.append(self.create_group("cluster", self.cluster.id, "cluster"))
        groups.append(self.create_group("service_1", self.service_1.id, "clusterobject"))
        groups.append(self.create_group("service_2", self.service_2.id, "clusterobject"))
        groups.append(self.create_group("component_1", self.component_11.id, "servicecomponent"))
        for group in groups:
            group.hosts.add(self.host)
            update_obj_config(
                group.config, {"some_string": group.name}, {"group_keys": {"some_string": True}}
            )

    @staticmethod
    def create_group(name, object_id, model_name):
        return GroupConfig.objects.create(
            object_id=object_id, object_type=ContentType.objects.get(model=model_name), name=name
        )

    def test_host_vars(self):
        self.assertDictEqual(
            get_host_vars(self.host, self.cluster)["cluster"]["config"], {"some_string": "cluster"}
        )

        service_1_host_vars = get_host_vars(self.host, self.service_1)
        self.assertDictEqual(
            service_1_host_vars["services"]["service_1"]["config"], {"some_string": "service_1"}
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_2"]["config"], {"some_string": "service_2"}
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_1"]["component_11"]["config"],
            {"some_string": "component_1"},
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_1"]["component_12"]["config"],
            {"some_string": "some_string"},
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_2"]["component_21"]["config"],
            {"some_string": "some_string"},
        )

        component_11_host_vars = get_host_vars(self.host, self.component_11)
        self.assertDictEqual(
            component_11_host_vars["services"]["service_1"]["config"], {"some_string": "service_1"}
        )
        self.assertDictEqual(
            component_11_host_vars["services"]["service_1"]["component_11"]["config"],
            {"some_string": "component_1"},
        )
        self.assertDictEqual(
            component_11_host_vars["services"]["service_1"]["component_12"]["config"],
            {"some_string": "some_string"},
        )
        self.assertFalse("service_2" in component_11_host_vars["services"].keys())

        component_12_host_vars = get_host_vars(self.host, self.component_12)
        self.assertDictEqual(component_12_host_vars, {})
