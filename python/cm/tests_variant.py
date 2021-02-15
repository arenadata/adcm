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
from cm.variant import variant_host
from cm.errors import AdcmEx
from cm.models import Cluster, ClusterObject, ServiceComponent, HostComponent
from cm.models import Bundle, Prototype


class TestVariantHost(TestCase):
    add_hc = HostComponent.objects.create

    def cook_cluster(self):
        b = Bundle.objects.create(name="ADH", version="1.0")
        proto = Prototype.objects.create(type="cluster", name="ADH", bundle=b)
        return Cluster.objects.create(prototype=proto)

    def cook_provider(self):
        b = Bundle.objects.create(name="SSH", version="1.0")
        pp = Prototype.objects.create(type="provider", bundle=b)
        provider = add_host_provider(pp, 'SSHone')
        host_proto = Prototype.objects.create(bundle=b, type='host')
        return (provider, host_proto)

    def cook_service(self, cluster):
        proto = Prototype.objects.create(
            type="service", name="UBER", bundle=cluster.prototype.bundle
        )
        return ClusterObject.objects.create(cluster=cluster, prototype=proto)

    def cook_component(self, cluster, service, name):
        proto = Prototype.objects.create(
            type="component", name=name, bundle=cluster.prototype.bundle, parent=service.prototype
        )
        return ServiceComponent.objects.create(
            cluster=cluster, service=service, prototype=proto
        )

    def test_no_host_in_cluster(self):
        cls = self.cook_cluster()
        hosts = variant_host(cls, {'in_cluster': None})
        self.assertEqual(hosts, [])

    def test_host_in_cluster(self):
        cls = self.cook_cluster()
        provider, hp = self.cook_provider()
        h1 = add_host(hp, provider, 'h10')
        add_host_to_cluster(cls, h1)
        hosts = variant_host(cls, {'in_cluster': []})
        self.assertEqual(hosts, ['h10'])

    def test_tuple(self):
        cls = self.cook_cluster()
        self.cook_service(cls)
        try:
            variant_host(cls, {'in_service': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of "in_service" predicate should be a list')
        try:
            variant_host(cls, {'in_service': {}})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of "in_service" predicate should be a list')
        try:
            variant_host(cls, {'in_service': [123]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'tuple item of predicate "in_service" shoud be a map')
        try:
            variant_host(cls, {'in_service': [{}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "tuple" key in predicate "in_service" arguments')
        try:
            variant_host(cls, {'in_service': [{'tuple': 123}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'value of tuple of predicate "in_service" shoud be a list')
        try:
            variant_host(cls, {'in_service': [{'tuple': []}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'wrong number of items in tuple for predicate "in_service"')
        try:
            variant_host(cls, {'in_service': [{'tuple': [1]}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'wrong number of items in tuple for predicate "in_service"')
        try:
            variant_host(cls, {'in_service': [{'tuple': [1, 2, 3]}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'wrong number of items in tuple for predicate "in_service"')
        try:
            variant_host(cls, {'in_service': [{'tuple': [1, 2]}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "service" tuple for predicate "in_service"')
        hosts = variant_host(
            cls, {'in_service': [{'tuple': ['service', 'UBER']}]}
        )
        self.assertEqual(hosts, [])

    def test_host_in_service(self):
        cls = self.cook_cluster()
        service = self.cook_service(cls)
        comp = self.cook_component(cls, service, 'Server')
        provider, hp = self.cook_provider()
        h1 = add_host(hp, provider, 'h10')
        add_host_to_cluster(cls, h1)
        self.add_hc(cluster=cls, service=service, component=comp, host=h1)
        try:
            variant_host(cls, {'in_service': [{'tuple': [1, 2]}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "service" tuple for predicate "in_service"')
        try:
            variant_host(cls, {'in_service': [{'tuple': ['service', 'qwe']}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'service "qwe" is not found')
        args = {'in_service': [{'tuple': ['service', 'UBER']}]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h10'])

    def test_host_in_component(self):
        cls = self.cook_cluster()
        service = self.cook_service(cls)
        comp1 = self.cook_component(cls, service, 'Server')
        comp2 = self.cook_component(cls, service, 'Node')
        provider, hp = self.cook_provider()
        h1 = add_host(hp, provider, 'h10')
        h2 = add_host(hp, provider, 'h11')
        add_host_to_cluster(cls, h1)
        add_host_to_cluster(cls, h2)
        self.add_hc(cluster=cls, service=service, component=comp1, host=h1)
        self.add_hc(cluster=cls, service=service, component=comp2, host=h2)
        try:
            variant_host(cls, {'in_component': [{'tuple': [1, 2]}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "service" tuple for predicate "in_component"')
        try:
            variant_host(cls, {'in_component': [{'tuple': ['service', 'qwe']}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "component" tuple for predicate "in_component"')
        try:
            args = {'in_component': [{'tuple': ['service', 'x']}, {'tuple': ['component', 'z']}]}
            variant_host(cls, args)
        except AdcmEx as e:
            self.assertEqual(e.msg, 'service "x" is not found')
        try:
            args = {'in_component': [{'tuple': ['service', 'UBER']}, {'tuple': ['component', 'z']}]}
        except AdcmEx as e:
            self.assertEqual(e.msg, 'service "x" is not found')
        args = {'in_component': [{'tuple': ['service', 'UBER']}, {'tuple': ['component', 'Node']}]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, ['h11'])

    def test_host_and(self):
        cls = self.cook_cluster()
        service = self.cook_service(cls)
        comp1 = self.cook_component(cls, service, 'Server')
        comp2 = self.cook_component(cls, service, 'Node')
        provider, hp = self.cook_provider()
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
            variant_host(cls, {'and': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of "and" predicate should be a list')
        try:
            variant_host(cls, {'and': [123]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of process_args should be a map')
        try:
            variant_host(cls, {'and': [{"qwe": 123}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')
        self.assertEqual(variant_host(cls, {'and': []}), [])
        args = {
            'and': [
                {'in_service': [{'tuple': ['service', 'UBER']}]},
                {'in_component': [
                    {'tuple': ['service', 'UBER']},
                    {'tuple': ['component', 'Node']}
                ]},
        ]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, {'h11', 'h12'})

    def test_host_or(self):
        cls = self.cook_cluster()
        service = self.cook_service(cls)
        comp1 = self.cook_component(cls, service, 'Server')
        comp2 = self.cook_component(cls, service, 'Node')
        comp3 = self.cook_component(cls, service, 'Secondary')
        provider, hp = self.cook_provider()
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
            variant_host(cls, {'or': 123})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of "or" predicate should be a list')
        try:
            variant_host(cls, {'or': [123]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'arguments of process_args should be a map')
        try:
            variant_host(cls, {'or': [{"qwe": 123}]})
        except AdcmEx as e:
            self.assertEqual(e.msg, 'no "qwe" in list of host functions')
        self.assertEqual(variant_host(cls, {'or': []}), [])
        args = {
            'or': [
                {'in_component': [
                    {'tuple': ['service', 'UBER']},
                    {'tuple': ['component', 'Server']}
                ]},
                {'in_component': [
                    {'tuple': ['service', 'UBER']},
                    {'tuple': ['component', 'Secondary']}
                ]},
        ]}
        hosts = variant_host(cls, args)
        self.assertEqual(hosts, {'h10', 'h12'})
