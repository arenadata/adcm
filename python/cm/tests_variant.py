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

from django.test import TestCase

from cm.api import add_host, add_host_to_cluster, add_host_provider
from cm.variant import get_variant, variant_host, var_host_solver, VARIANT_HOST_FUNC
from cm.errors import AdcmEx
from cm.models import Cluster, ClusterObject, ServiceComponent, HostComponent
from cm.models import Bundle, Prototype


def cook_cluster():
    b = Bundle.objects.create(name="ADH", version="1.0")
    proto = Prototype.objects.create(type="cluster", name="ADH", bundle=b)
    return Cluster.objects.create(prototype=proto)


def cook_provider():
    b = Bundle.objects.create(name="SSH", version="1.0")
    pp = Prototype.objects.create(type="provider", bundle=b)
    provider = add_host_provider(pp, 'SSHone')
    host_proto = Prototype.objects.create(bundle=b, type='host')
    return (provider, host_proto)


def cook_service(cluster):
    proto = Prototype.objects.create(type="service", name="UBER", bundle=cluster.prototype.bundle)
    return ClusterObject.objects.create(cluster=cluster, prototype=proto)


def cook_component(cluster, service, name):
    proto = Prototype.objects.create(
        type="component", name=name, bundle=cluster.prototype.bundle, parent=service.prototype
    )
    return ServiceComponent.objects.create(cluster=cluster, service=service, prototype=proto)


class TestVariantInline(TestCase):
    def test_inline(self):
        limits = {"source": {"type": "inline", "value": [1, 2, 3]}}
        self.assertEqual(get_variant(None, None, limits), [1, 2, 3])


class TestVariantBuiltIn(TestCase):
    add_hc = HostComponent.objects.create

    def test_host_in_cluster_no_host(self):
        cls = cook_cluster()
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        self.assertEqual(get_variant(cls, None, limits), [])

    def test_host_in_cluster(self):
        cls = cook_cluster()
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        self.assertEqual(get_variant(cls, None, limits), [])
        add_host_to_cluster(cls, h1)
        self.assertEqual(get_variant(cls, None, limits), ['h10'])

    def test_host_in_cluster_service(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        self.assertEqual(get_variant(cls, None, limits), [])
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        self.assertEqual(get_variant(cls, None, limits), ['h10', 'h11'])
        limits['source']['args'] = {'service': 'QWE'}
        self.assertEqual(get_variant(cls, None, limits), [])
        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)
        self.assertEqual(get_variant(cls, None, limits), [])
        limits['source']['args']['service'] = 'UBER'
        self.assertEqual(get_variant(cls, None, limits), ['h11'])

    def test_host_in_cluster_component(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        comp2 = cook_component(cls, service, 'Node')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        h3 = add_host(hp, provider, 'h12')
        limits = {"source": {"type": "builtin", "name": "host_in_cluster"}}
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.assertEqual(get_variant(cls, None, limits), ['h10', 'h11', 'h12'])
        limits['source']['args'] = {'service': 'UBER', 'component': 'QWE'}
        self.assertEqual(get_variant(cls, None, limits), [])
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.assertEqual(get_variant(cls, None, limits), [])
        limits['source']['args']['component'] = 'Node'
        self.assertEqual(get_variant(cls, None, limits), ['h11'])


class TestVariantHost(TestCase):
    add_hc = HostComponent.objects.create

    def test_solver(self):
        cls = cook_cluster()
        try:
            self.assertEqual(variant_host(cls, {'any': 'dict'}), {'any': 'dict'})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "predicate" key in variant host function arguments')
        try:
            self.assertEqual(variant_host(cls, {}), {})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "predicate" key in variant host function arguments')
        try:
            self.assertEqual(variant_host(cls, []), [])
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of variant host function should be a map')
        try:
            variant_host(cls, 42)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of variant host function should be a map')
        try:
            variant_host(cls, 'qwe')
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of variant host function should be a map')
        try:
            variant_host(cls, {'predicate': 'qwe'})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')
        try:
            variant_host(cls, {'predicate': 'inline_list'})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "args" key in solver args')
        try:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"qwe": 1}])
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "predicate" key in solver args')
        try:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"predicate": 'qwe'}])
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "args" key in solver args')
        try:
            var_host_solver(cls, VARIANT_HOST_FUNC, [{"predicate": 'qwe', 'args': {}}])
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')

        args = {'predicate': 'inline_list', 'args': {'list': [1, 2, 3]}}
        self.assertEqual(variant_host(cls, args), [1, 2, 3])
        args = {'predicate': 'and', 'args': [
            {'predicate': 'inline_list', 'args': {'list': [1, 2, 3]}},
            {'predicate': 'inline_list', 'args': {'list': [2, 3, 4]}},
        ]}
        self.assertEqual(variant_host(cls, args), [2, 3])
        args = {'predicate': 'or', 'args': [
            {'predicate': 'inline_list', 'args': {'list': [1, 2, 3]}},
            {'predicate': 'inline_list', 'args': {'list': [2, 3, 4]}},
        ]}
        self.assertEqual(variant_host(cls, args), [1, 2, 3, 4])
        args = {'predicate': 'or', 'args': [
            {'predicate': 'inline_list', 'args': {'list': [1, 2, 3]}},
        ]}
        self.assertEqual(variant_host(cls, args), [1, 2, 3])

    def test_no_host_in_cluster(self):
        cls = cook_cluster()
        hosts = variant_host(cls, {'predicate': 'in_cluster', 'args': None})
        self.assertEqual(hosts, [])
        hosts = variant_host(cls, {'predicate': 'in_cluster', 'args': []})
        self.assertEqual(hosts, [])
        hosts = variant_host(cls, {'predicate': 'in_cluster', 'args': {}})
        self.assertEqual(hosts, [])

    def test_host_in_cluster(self):
        cls = cook_cluster()
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        add_host_to_cluster(cls, h1)
        hosts = variant_host(cls, {'predicate': 'in_cluster', 'args': []})
        self.assertEqual(hosts, ['h10'])

    def test_host_in_service(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp = cook_component(cls, service, 'Server')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        add_host_to_cluster(cls, h1)
        self.add_hc(cluster=cls, service=service, component=comp, host=h1)
        try:
            variant_host(cls, {'predicate': 'in_service', 'args': {}})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "service" tuple for predicate "in_service"')
        try:
            variant_host(cls, {'predicate': 'in_service', 'args': {'service': 'qwe'}})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'service "qwe" is not found')
        args = {'predicate': 'in_service', 'args': {'service': 'UBER'}}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h10'])

    def test_host_in_component(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        comp2 = cook_component(cls, service, 'Node')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        try:
            variant_host(cls, {'predicate': 'in_component'})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "args" key in solver args')
        try:
            variant_host(cls, {'predicate': 'in_component', 'args': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of solver should be a list or a map')
        try:
            variant_host(cls, {'predicate': 'in_component', 'args': []})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "service" tuple for predicate "in_component"')
        try:
            variant_host(cls, {'predicate': 'in_component', 'args': {'service': 'qwe'}})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "component" tuple for predicate "in_component"')
        try:
            args = {'predicate': 'in_component', 'args': {'service': 'qwe', 'component': 'asd'}}
            variant_host(cls, args)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'service "qwe" is not found')
        try:
            args = {'predicate': 'in_component', 'args': {'service': 'UBER', 'component': 'asd'}}
            variant_host(cls, args)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'component "asd" is not found')

        args = {'predicate': 'in_component', 'args': {'service': 'UBER', 'component': 'Node'}}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h11'])

    def test_host_and(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        comp2 = cook_component(cls, service, 'Node')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        h3 = add_host(hp, provider, 'h12')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h3)
        try:
            variant_host(cls, {'predicate': 'and', 'args': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of solver should be a list or a map')
        try:
            variant_host(cls, {'predicate': 'and', 'args': [123]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'predicte item should be a map')
        try:
            args = {'predicate': 'and', 'args': [{'predicate': 'qwe', 'args': 123}]}
            variant_host(cls, args)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')
        self.assertEqual(variant_host(cls, {'predicate': 'and', 'args': []}), [])
        args = {'predicate': 'and', 'args': [
            {'predicate': 'in_service', 'args': {'service': 'UBER'}},
            {'predicate': 'in_component', 'args': {'service': 'UBER', 'component': 'Node'}},
        ]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h11', 'h12'])

    def test_host_or(self):
        cls = cook_cluster()
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        comp2 = cook_component(cls, service, 'Node')
        comp3 = cook_component(cls, service, 'Secondary')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        h3 = add_host(hp, provider, 'h12')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        add_host_to_cluster(cls, h3)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        self.add_hc(cluster=cls, service=service, component=comp3, host=h3)
        try:
            variant_host(cls, {'predicate': 'or', 'args': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of solver should be a list or a map')
        try:
            variant_host(cls, {'predicate': 'or', 'args': [123]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'predicte item should be a map')
        try:
            variant_host(cls, {'predicate': 'or', 'args': [{"qwe": 123}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "predicate" key in solver args')
        try:
            variant_host(cls, {'predicate': 'or', 'args': [{'predicate': 'qwe'}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "args" key in solver args')
        try:
            args = {'predicate': 'or', 'args': [{'predicate': 'qwe', 'args': 123}]}
            variant_host(cls, args)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')
        self.assertEqual(variant_host(cls, {'predicate': 'or', 'args': []}), [])
        args = {
            'predicate': 'or', 'args': [
                {'predicate': 'in_component', 'args': {
                    'service': 'UBER',
                    'component': 'Server',
                }},
                {'predicate': 'in_component', 'args': {
                    'service': 'UBER',
                    'component': 'Secondary',
                }},
            ]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h10', 'h12'])

    def test_host_in_hc(self):
        cls = cook_cluster()
        self.assertEqual(variant_host(cls, {'predicate': 'in_hc', 'args': None}), [])
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        self.assertEqual(variant_host(cls, {'predicate': 'in_hc', 'args': None}), [])
        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)
        self.assertEqual(variant_host(cls, {'predicate': 'in_hc', 'args': None}), ['h11'])

    def test_host_not_in_hc(self):
        cls = cook_cluster()
        self.assertEqual(variant_host(cls, {'predicate': 'not_in_hc', 'args': None}), [])
        service = cook_service(cls)
        comp1 = cook_component(cls, service, 'Server')
        provider, hp = cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        hosts = variant_host(cls, {'predicate': 'not_in_hc', 'args': None})
        self.assertEqual(hosts, ['h10', 'h11'])
        self.add_hc(cluster=cls, service=service, component=comp1, host=h2)
        self.assertEqual(variant_host(cls, {'predicate': 'not_in_hc', 'args': None}), ['h10'])
