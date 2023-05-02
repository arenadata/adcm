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
# pylint: disable=wrong-import-order


from cm.hierarchy import HierarchyError, Tree
from cm.tests.utils import (
    gen_bundle,
    gen_cluster,
    gen_component,
    gen_host,
    gen_host_component,
    gen_prototype,
    gen_provider,
    gen_service,
)

from adcm.tests.base import BaseTestCase


def generate_hierarchy():  # pylint: disable=too-many-locals,too-many-statements
    """
    Generates two hierarchies:
    cluster_1 - service_11 - component_111 - host_11 - provider_1
                                           - host_12 - provider_1
                           - component_112 - host_11 - provider_1
                                           - host_12 - provider_1
              - service_12 - component_121 - host_11 - provider_1
                                           - host_12 - provider_1
                                           - host_31 - provider_3
                           - component_122 - host_11 - provider_1
                                           - host_12 - provider_1
                                           - host_31 - provider_3
    cluster_2 - service_21 - component_211 - host_21 - provider_2
                                           - host_22 - provider_2
                           - component_212 - host_21 - provider_2
                                           - host_22 - provider_2
              - service_22 - component_221 - host_21 - provider_2
                                           - host_22 - provider_2
                                           - host_32 - provider_3
                           - component_222 - host_21 - provider_2
                                           - host_22 - provider_2
                                           - host_32 - provider_3
    """
    cluster_bundle = gen_bundle()

    cluster_pt = gen_prototype(cluster_bundle, "cluster")
    service_pt_1 = gen_prototype(cluster_bundle, "service")
    service_pt_2 = gen_prototype(cluster_bundle, "service")
    component_pt_11 = gen_prototype(cluster_bundle, "component")
    component_pt_12 = gen_prototype(cluster_bundle, "component")
    component_pt_21 = gen_prototype(cluster_bundle, "component")
    component_pt_22 = gen_prototype(cluster_bundle, "component")

    cluster_1 = gen_cluster(prototype=cluster_pt)
    service_11 = gen_service(cluster_1, prototype=service_pt_1)
    service_12 = gen_service(cluster_1, prototype=service_pt_2)
    component_111 = gen_component(service_11, prototype=component_pt_11)
    component_112 = gen_component(service_11, prototype=component_pt_12)
    component_121 = gen_component(service_12, prototype=component_pt_21)
    component_122 = gen_component(service_12, prototype=component_pt_22)

    cluster_2 = gen_cluster(prototype=cluster_pt)
    service_21 = gen_service(cluster_2, prototype=service_pt_1)
    service_22 = gen_service(cluster_2, prototype=service_pt_2)
    component_211 = gen_component(service_21, prototype=component_pt_11)
    component_212 = gen_component(service_21, prototype=component_pt_12)
    component_221 = gen_component(service_22, prototype=component_pt_21)
    component_222 = gen_component(service_22, prototype=component_pt_22)

    provider_bundle = gen_bundle()

    provider_pt = gen_prototype(provider_bundle, "provider")
    host_pt = gen_prototype(provider_bundle, "host")

    provider_1 = gen_provider(prototype=provider_pt)
    host_11 = gen_host(provider_1, prototype=host_pt)
    host_12 = gen_host(provider_1, prototype=host_pt)

    provider_2 = gen_provider(prototype=provider_pt)
    host_21 = gen_host(provider_2, prototype=host_pt)
    host_22 = gen_host(provider_2, prototype=host_pt)

    provider_3 = gen_provider(prototype=provider_pt)
    host_31 = gen_host(provider_3, prototype=host_pt)
    host_32 = gen_host(provider_3, prototype=host_pt)

    gen_host_component(component_111, host_11)
    gen_host_component(component_112, host_11)
    gen_host_component(component_121, host_11)
    gen_host_component(component_122, host_11)

    gen_host_component(component_111, host_12)
    gen_host_component(component_112, host_12)
    gen_host_component(component_121, host_12)
    gen_host_component(component_122, host_12)

    gen_host_component(component_121, host_31)
    gen_host_component(component_122, host_31)

    gen_host_component(component_211, host_21)
    gen_host_component(component_212, host_21)
    gen_host_component(component_221, host_21)
    gen_host_component(component_222, host_21)

    gen_host_component(component_211, host_22)
    gen_host_component(component_212, host_22)
    gen_host_component(component_221, host_22)
    gen_host_component(component_222, host_22)

    gen_host_component(component_221, host_32)
    gen_host_component(component_222, host_32)

    return {
        "cluster_1": cluster_1,
        "service_11": service_11,
        "service_12": service_12,
        "component_111": component_111,
        "component_112": component_112,
        "component_121": component_121,
        "component_122": component_122,
        "cluster_2": cluster_2,
        "service_21": service_21,
        "service_22": service_22,
        "component_211": component_211,
        "component_212": component_212,
        "component_221": component_221,
        "component_222": component_222,
        "provider_1": provider_1,
        "host_11": host_11,
        "host_12": host_12,
        "provider_2": provider_2,
        "host_21": host_21,
        "host_22": host_22,
        "provider_3": provider_3,
        "host_31": host_31,
        "host_32": host_32,
    }


class HierarchyTest(BaseTestCase):
    def test_get_node(self):
        """Test function `hierarchy.Tree.get_node()` AND if tree was built correctly"""
        hierarchy_objects = generate_hierarchy()
        tree = Tree(hierarchy_objects["cluster_1"])
        expected = (
            "cluster_1",
            "service_11",
            "service_12",
            "component_111",
            "component_112",
            "component_121",
            "component_122",
            "host_11",
            "host_12",
            "host_31",
        )
        for name in expected:
            assert tree.get_node(hierarchy_objects[name])

        not_expected = (
            "cluster_2",
            "service_21",
            "service_22",
            "component_211",
            "component_212",
            "component_221",
            "component_221",
            "host_21",
            "host_22",
            "host_32",
            "provider_2",
        )
        for name in not_expected:
            with self.assertRaises(HierarchyError):
                tree.get_node(hierarchy_objects[name])

    def test_get_directly_affected(self):
        hierarchy_objects = generate_hierarchy()
        tree = Tree(hierarchy_objects["cluster_1"])

        expected = {
            "cluster_1": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "service_11": (
                "cluster_1",
                "service_11",
                "component_111",
                "component_112",
                "host_11",
                "host_12",
            ),
            "service_12": (
                "cluster_1",
                "service_12",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "component_111": (
                "cluster_1",
                "service_11",
                "component_111",
                "host_11",
                "host_12",
            ),
            "component_112": (
                "cluster_1",
                "service_11",
                "component_112",
                "host_11",
                "host_12",
            ),
            "component_121": (
                "cluster_1",
                "service_12",
                "component_121",
                "host_11",
                "host_12",
                "host_31",
            ),
            "component_122": (
                "cluster_1",
                "service_12",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "host_11": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
            ),
            "host_12": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_12",
            ),
            "host_31": (
                "cluster_1",
                "service_12",
                "component_121",
                "component_122",
                "host_31",
            ),
        }

        for target_object, affected_objects in expected.items():
            target_node = tree.get_node(hierarchy_objects[target_object])
            expected_affected = {tree.get_node(hierarchy_objects[name]) for name in affected_objects}
            got_affected = set(tree.get_directly_affected(target_node))

            self.assertSetEqual(expected_affected, got_affected)

    def test_get_all_affected(self):
        hierarchy_objects = generate_hierarchy()
        tree = Tree(hierarchy_objects["cluster_1"])

        expected = {
            "cluster_1": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "service_11": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
            ),
            "service_12": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "component_111": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
            ),
            "component_112": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
            ),
            "component_121": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "component_122": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
                "host_12",
                "host_31",
            ),
            "host_11": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_11",
            ),
            "host_12": (
                "cluster_1",
                "service_11",
                "service_12",
                "component_111",
                "component_112",
                "component_121",
                "component_122",
                "host_12",
            ),
            "host_31": (
                "cluster_1",
                "service_12",
                "component_121",
                "component_122",
                "host_31",
            ),
        }

        for target_object, affected_objects in expected.items():
            target_node = tree.get_node(hierarchy_objects[target_object])
            expected_affected = {tree.get_node(hierarchy_objects[name]) for name in affected_objects}
            got_affected = set(tree.get_all_affected(target_node))

            self.assertSetEqual(expected_affected, got_affected)
