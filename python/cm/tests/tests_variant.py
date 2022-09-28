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

from adcm.tests.base import BaseTestCase
from cm.api import add_host, add_host_provider, add_host_to_cluster
from cm.errors import AdcmEx
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    HostComponent,
    Prototype,
    ServiceComponent,
)
from cm.variant import VARIANT_HOST_FUNC, get_variant, var_host_solver, variant_host


def cook_cluster():
    b = Bundle.objects.create(name="ADH", version="1.0")
    proto = Prototype.objects.create(type="cluster", name="ADH", bundle=b)

    return Cluster.objects.create(prototype=proto, name="Blue Tiber")


def cook_provider():
    b = Bundle.objects.create(name="SSH", version="1.0")
    pp = Prototype.objects.create(type="provider", bundle=b)
    provider = add_host_provider(pp, "SSHone")
    host_proto = Prototype.objects.create(bundle=b, type="host")

    return provider, host_proto


def cook_service(cluster, name="UBER"):
    proto = Prototype.objects.create(type="service", name=name, bundle=cluster.prototype.bundle)

    return ClusterObject.objects.create(cluster=cluster, prototype=proto)


def cook_component(cluster, service, name):
    proto = Prototype.objects.create(
        type="component", name=name, bundle=cluster.prototype.bundle, parent=service.prototype
    )

    return ServiceComponent.objects.create(cluster=cluster, service=service, prototype=proto)


class TestVariantInline(BaseTestCase):
    def test_inline(self):
        limits = {"source": {"type": "inline", "value": [1, 2, 3]}}

        self.assertEqual(get_variant(None, None, limits), [1, 2, 3])


class TestVariantBuiltIn(BaseTestCase):
    add_hc = HostComponent.objects.create

    def test_host_in_cluster_no_host(self):
        cls = cook_cluster()
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}

        self.assertEqual(get_variant(cls, None, limits), [])

    def test_host_in_cluster(self):
        cls = cook_cluster()
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}

        self.assertEqual(get_variant(cls, None, limits), [])

        add_host_to_cluster(cls, h1)

        self.assertEqual(get_variant(cls, None, limits), ["h10"])

    def test_host_in_cluster_service(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        self.assertEqual(get_variant(cls, None, limits), [])
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)

        self.assertEqual(get_variant(cls, None, limits), ["h10", "h11"])

        limits["source"]["args"] = {"service": "QWE"}

        self.assertEqual(get_variant(cls, None, limits), [])

        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)

        self.assertEqual(get_variant(cls, None, limits), [])

        limits["source"]["args"]["service"] = "UBER"

        self.assertEqual(get_variant(cls, None, limits), ["h11"])

    def test_host_in_cluster_component(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        comp2 = cook_component(cls, service, "Node")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        h3 = add_host(hp, provider, "h12")
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)

        self.assertEqual(get_variant(cls, None, limits), ["h10", "h11", "h12"])

        limits["source"]["args"] = {"service": "UBER", "component": "QWE"}

        self.assertEqual(get_variant(cls, None, limits), [])

        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)

        self.assertEqual(get_variant(cls, None, limits), [])

        limits["source"]["args"]["component"] = "Node"

        self.assertEqual(get_variant(cls, None, limits), ["h11"])


class TestVariantHost(BaseTestCase):
    add_hc = HostComponent.objects.create

    def test_solver(self):
        cls = cook_cluster()
        with self.assertRaises(AdcmEx) as e:
            self.assertEqual(variant_host(cls, {"any": "dict"}), {"any": "dict"})

        self.assertEqual(e.exception.msg, 'no "predicate" key in variant host function arguments')

        with self.assertRaises(AdcmEx) as e:
            self.assertEqual(variant_host(cls, {}), {})

        self.assertEqual(e.exception.msg, 'no "predicate" key in variant host function arguments')

        with self.assertRaises(AdcmEx) as e:
            self.assertEqual(variant_host(cls, []), [])

        self.assertEqual(e.exception.msg, "arguments of variant host function should be a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, 42)

        self.assertEqual(e.exception.msg, "arguments of variant host function should be a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, "qwe")

        self.assertEqual(e.exception.msg, "arguments of variant host function should be a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "qwe"})

        self.assertEqual(e.exception.msg, 'no "qwe" in list of host functions')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "inline_list"})

        self.assertEqual(e.exception.msg, 'no "args" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"qwe": 1}])

        self.assertEqual(e.exception.msg, 'no "predicate" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"predicate": "qwe"}])

        self.assertEqual(e.exception.msg, 'no "args" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"predicate": "qwe", "args": {}}])

        self.assertEqual(e.exception.msg, 'no "qwe" in list of host functions')

        args = {"predicate": "inline_list", "args": {"list": [1, 2, 3]}}

        self.assertEqual(variant_host(cls, args), [1, 2, 3])

        args = {
            "predicate": "and",
            "args": [
                {"predicate": "inline_list", "args": {"list": [1, 2, 3]}},
                {"predicate": "inline_list", "args": {"list": [2, 3, 4]}},
            ],
        }

        self.assertEqual(variant_host(cls, args), [2, 3])

        args = {
            "predicate": "or",
            "args": [
                {"predicate": "inline_list", "args": {"list": [1, 2, 3]}},
                {"predicate": "inline_list", "args": {"list": [2, 3, 4]}},
            ],
        }

        self.assertEqual(variant_host(cls, args), [1, 2, 3, 4])

        args = {
            "predicate": "or",
            "args": [
                {"predicate": "inline_list", "args": {"list": [1, 2, 3]}},
            ],
        }

        self.assertEqual(variant_host(cls, args), [1, 2, 3])

    def test_no_host_in_cluster(self):
        cls = cook_cluster()
        hosts = variant_host(cls, {"predicate": "in_cluster", "args": None})

        self.assertEqual(hosts, [])

        hosts = variant_host(cls, {"predicate": "in_cluster", "args": []})

        self.assertEqual(hosts, [])

        hosts = variant_host(cls, {"predicate": "in_cluster", "args": {}})

        self.assertEqual(hosts, [])

    def test_host_in_cluster(self):
        cls = cook_cluster()
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        add_host_to_cluster(cls, h1)
        hosts = variant_host(cls, {"predicate": "in_cluster", "args": []})

        self.assertEqual(hosts, ["h10"])

    def test_host_in_service(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp = cook_component(cls, service, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        add_host_to_cluster(cls, h1)

        self.add_hc(cluster=cls, service=service, component=comp, host=h1)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_service", "args": {}})

        self.assertEqual(e.exception.msg, 'no "service" argument for predicate "in_service"')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_service", "args": {"service": "qwe"}})

        self.assertTrue("ClusterObject {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        args = {"predicate": "in_service", "args": {"service": "UBER"}}
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h10"])

    def test_host_not_in_service(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp = cook_component(cls, service, "Server")
        service2 = cook_service(cls, "Gett")
        comp2 = cook_component(cls, service2, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        h3 = add_host(hp, provider, "h12")
        add_host(hp, provider, "h13")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.add_hc(cluster=cls, service=service, component=comp, host=h1)
        self.add_hc(cluster=cls, service=service2, component=comp2, host=h3)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "not_in_service", "args": {}})

        self.assertEqual(e.exception.msg, 'no "service" argument for predicate "not_in_service"')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "not_in_service", "args": {"service": "qwe"}})

        self.assertTrue("ClusterObject {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        args = {"predicate": "not_in_service", "args": {"service": "UBER"}}
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h11", "h12"])

        args = {"predicate": "not_in_service", "args": {"service": "Gett"}}
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h10", "h11"])

    def test_host_in_component(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        comp2 = cook_component(cls, service, "Node")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_component"})

        self.assertEqual(e.exception.msg, 'no "args" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_component", "args": 123})

        self.assertEqual(e.exception.msg, "arguments of solver should be a list or a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_component", "args": []})

        self.assertEqual(e.exception.msg, 'no "service" argument for predicate "in_component"')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "in_component", "args": {"service": "qwe"}})

        self.assertTrue("ClusterObject {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        with self.assertRaises(AdcmEx) as e:
            args = {"predicate": "in_component", "args": {"service": "UBER", "component": "asd"}}
            variant_host(cls, args)

        self.assertTrue("ServiceComponent {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        args = {"predicate": "in_component", "args": {"service": "UBER", "component": "Node"}}
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h11"])

    def test_host_not_in_component(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        comp2 = cook_component(cls, service, "Node")
        service2 = cook_service(cls, "Gett")
        comp3 = cook_component(cls, service2, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        h3 = add_host(hp, provider, "h12")
        h4 = add_host(hp, provider, "h13")
        add_host(hp, provider, "h14")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        add_host_to_cluster(cls, h4)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.add_hc(cluster=cls, service=service2, component=comp3, host=h3)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "not_in_component", "args": []})

        self.assertEqual(e.exception.msg, 'no "service" argument for predicate "not_in_component"')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "not_in_component", "args": {"service": "qwe"}})

        self.assertTrue("ClusterObject {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        with self.assertRaises(AdcmEx) as e:
            args = {
                "predicate": "not_in_component",
                "args": {"service": "UBER", "component": "asd"},
            }
            variant_host(cls, args)

        self.assertTrue("ServiceComponent {" in e.exception.msg)
        self.assertTrue("} does not exist" in e.exception.msg)

        args = {"predicate": "not_in_component", "args": {"service": "UBER", "component": "Node"}}

        self.assertEqual(variant_host(cls, args), ["h10", "h12", "h13"])

        args = {"predicate": "not_in_component", "args": {"service": "UBER", "component": "Server"}}

        self.assertEqual(variant_host(cls, args), ["h11", "h12", "h13"])

        args = {"predicate": "not_in_component", "args": {"service": "Gett", "component": "Server"}}

        self.assertEqual(variant_host(cls, args), ["h10", "h11", "h13"])

    def test_host_and(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        comp2 = cook_component(cls, service, "Node")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        h3 = add_host(hp, provider, "h12")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h3)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "and", "args": 123})

        self.assertEqual(e.exception.msg, "arguments of solver should be a list or a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "and", "args": [123]})

        self.assertEqual(e.exception.msg, "predicate item should be a map")

        with self.assertRaises(AdcmEx) as e:
            args = {"predicate": "and", "args": [{"predicate": "qwe", "args": 123}]}
            variant_host(cls, args)

        self.assertEqual(e.exception.msg, 'no "qwe" in list of host functions')

        self.assertEqual(variant_host(cls, {"predicate": "and", "args": []}), [])

        args = {
            "predicate": "and",
            "args": [
                {"predicate": "in_service", "args": {"service": "UBER"}},
                {"predicate": "in_component", "args": {"service": "UBER", "component": "Node"}},
            ],
        }
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h11", "h12"])

    def test_host_or(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        comp2 = cook_component(cls, service, "Node")
        comp3 = cook_component(cls, service, "Secondary")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        h3 = add_host(hp, provider, "h12")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.add_hc(cluster=cls, service=service, component=comp3, host=h3)

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "or", "args": 123})

        self.assertEqual(e.exception.msg, "arguments of solver should be a list or a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "or", "args": [123]})

        self.assertEqual(e.exception.msg, "predicate item should be a map")

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "or", "args": [{"qwe": 123}]})

        self.assertEqual(e.exception.msg, 'no "predicate" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            variant_host(cls, {"predicate": "or", "args": [{"predicate": "qwe"}]})

        self.assertEqual(e.exception.msg, 'no "args" key in solver args')

        with self.assertRaises(AdcmEx) as e:
            args = {"predicate": "or", "args": [{"predicate": "qwe", "args": 123}]}
            variant_host(cls, args)

        self.assertEqual(e.exception.msg, 'no "qwe" in list of host functions')

        self.assertEqual(variant_host(cls, {"predicate": "or", "args": []}), [])

        args = {
            "predicate": "or",
            "args": [
                {
                    "predicate": "in_component",
                    "args": {
                        "service": "UBER",
                        "component": "Server",
                    },
                },
                {
                    "predicate": "in_component",
                    "args": {
                        "service": "UBER",
                        "component": "Secondary",
                    },
                },
            ],
        }
        hosts = variant_host(cls, args)

        self.assertEqual(hosts, ["h10", "h12"])

    def test_host_in_hc(self):
        cls = cook_cluster()

        self.assertEqual(variant_host(cls, {"predicate": "in_hc", "args": None}), [])

        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)

        self.assertEqual(variant_host(cls, {"predicate": "in_hc", "args": None}), [])

        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)

        self.assertEqual(variant_host(cls, {"predicate": "in_hc", "args": None}), ["h11"])

    def test_host_not_in_hc(self):
        cls = cook_cluster()

        self.assertEqual(variant_host(cls, {"predicate": "not_in_hc", "args": None}), [])

        service = cook_service(cls)
        comp1 = cook_component(cls, service, "Server")
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, "h10")
        h2 = add_host(hp, provider, "h11")
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        hosts = variant_host(cls, {"predicate": "not_in_hc", "args": None})

        self.assertEqual(hosts, ["h10", "h11"])

        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)

        self.assertEqual(variant_host(cls, {"predicate": "not_in_hc", "args": None}), ["h10"])
