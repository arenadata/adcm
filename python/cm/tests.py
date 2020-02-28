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

from django.test import TestCase

import cm.api
import cm.job
from cm.models import Cluster, Host, ClusterObject, ServiceComponent, HostComponent
from cm.models import Bundle, Upgrade, Prototype, Component, Action
from cm.errors import AdcmEx, AdcmApiEx


class TestUpgradeVersion(TestCase):

    def cook_cluster(self):
        b = Bundle(name="ADH", version="1.0")
        proto = Prototype(type="cluster", name="ADH", bundle=b)
        return Cluster(prototype=proto, issue='{}')

    def cook_upgrade(self):
        return Upgrade(
            min_version="1.0",
            max_version="2.0",
            min_strict=False,
            max_strict=False,
            state_available='"any"'
        )

    def check_upgrade(self, obj, upgrade, result):
        ok, msg = cm.upgrade.check_upgrade(obj, upgrade)
        if not ok:
            print("check_upgrade msg: ", msg)
        self.assertEqual(ok, result)

    def test_version(self):
        obj = self.cook_cluster()
        upgrade = self.cook_upgrade()

        obj.prototype.version = "1.5"
        self.check_upgrade(obj, upgrade, True)

        obj.prototype.version = "2.5"
        self.check_upgrade(obj, upgrade, False)

        obj.prototype.version = "2.0"
        self.check_upgrade(obj, upgrade, True)

        obj.prototype.version = "1.0"
        self.check_upgrade(obj, upgrade, True)

    def test_strict_version(self):
        obj = self.cook_cluster()
        upgrade = self.cook_upgrade()
        upgrade.min_strict = True
        upgrade.max_strict = True

        obj.prototype.version = "1.5"
        self.check_upgrade(obj, upgrade, True)

        obj.prototype.version = "2.5"
        self.check_upgrade(obj, upgrade, False)

        obj.prototype.version = "1.0"
        self.check_upgrade(obj, upgrade, False)

        obj.prototype.version = "2.0"
        self.check_upgrade(obj, upgrade, False)

    def test_state(self):
        obj = self.cook_cluster()
        upgrade = self.cook_upgrade()
        upgrade.state_available = json.dumps(["installed", "any"])
        obj.prototype.version = "1.5"

        obj.state = "created"
        self.check_upgrade(obj, upgrade, False)

        obj.state = "installed"
        self.check_upgrade(obj, upgrade, True)

    def test_issue(self):
        obj = self.cook_cluster()
        obj.issue = json.dumps({"config": False})
        upgrade = self.cook_upgrade()
        self.check_upgrade(obj, upgrade, False)


class SetUp():
    def cook_cluster_bundle(self, ver):
        b = Bundle.objects.create(name='ADH', version=ver)
        b.save()
        Prototype.objects.create(type="cluster", name="ADH", version=ver, bundle=b)
        sp2 = Prototype.objects.create(type="service", name="hive", bundle=b)
        Component.objects.create(prototype=sp2, name='server')
        sp1 = Prototype.objects.create(type="service", name="hadoop", version=ver, bundle=b)
        Component.objects.create(prototype=sp1, name='server')
        Component.objects.create(prototype=sp1, name='node')
        return b

    def cook_provider_bundle(self, ver):
        b = Bundle.objects.create(name='DF', version=ver)
        b.save()
        Prototype.objects.create(type="provider", name="DF", version=ver, bundle=b)
        Prototype.objects.create(type="host", name="DfHost", version=ver, bundle=b)
        return b

    def cook_provider(self, bundle, name):
        pp = Prototype.objects.get(type="provider", bundle=bundle)
        provider = cm.api.add_host_provider(pp, name)
        host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
        cm.api.add_host(host_proto, provider, 'server02.inter.net')
        cm.api.add_host(host_proto, provider, 'server01.inter.net')
        return provider

    def cook_cluster(self, bundle, name):
        cp = Prototype.objects.get(type="cluster", bundle=bundle)
        cluster = cm.api.add_cluster(cp, name)
        sp2 = Prototype.objects.get(type="service", name="hive", bundle=bundle)
        cm.api.add_service_to_cluster(cluster, sp2)
        sp1 = Prototype.objects.get(type="service", name="hadoop", bundle=bundle)
        cm.api.add_service_to_cluster(cluster, sp1)
        return cluster

    def cook_upgrade(self, bundle):
        return Upgrade.objects.create(
            bundle=bundle,
            min_version="1.0",
            max_version="2.0",
            state_available='["created"]'
        )


class TestUpgrade(TestCase):

    def test_cluster_upgrade(self):
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        b2 = setup.cook_cluster_bundle('2.0')
        setup.cook_cluster(b1, 'Test0')
        cluster = setup.cook_cluster(b1, 'Test1')
        upgrade = setup.cook_upgrade(b2)

        co1 = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')

        try:
            r = cm.upgrade.do_upgrade(co1, upgrade)
            self.assertEqual(r, 'ok')
        except AdcmEx as e:
            self.assertEqual(e.code, 'UPGRADE_ERROR')
            self.assertEqual(e.msg, 'can upgrade only cluster or host provider')

        old_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b1)
        new_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)
        self.assertEqual(co1.prototype.id, old_proto.id)

        cm.upgrade.do_upgrade(cluster, upgrade)
        co2 = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        self.assertEqual(co1.id, co2.id)
        self.assertEqual(co2.prototype.id, new_proto.id)

    def test_hc(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        b2 = setup.cook_cluster_bundle('2.0')
        b3 = setup.cook_provider_bundle('1.0')

        cluster = setup.cook_cluster(b1, 'Test1')
        provider = setup.cook_provider(b3, "DF01")

        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')
        sc2 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='node')
        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')
        h2 = Host.objects.get(provider=provider, fqdn='server02.inter.net')
        cm.api.add_host_to_cluster(cluster, h1)
        cm.api.add_host_to_cluster(cluster, h2)

        hc = [
            {'service_id': co.id, 'host_id': h1.id, 'component_id': sc1.id},
            {'service_id': co.id, 'host_id': h2.id, 'component_id': sc2.id},
        ]
        cm.api.add_hc(cluster, hc)
        hc1 = HostComponent.objects.get(cluster=cluster, service=co, component=sc2)
        self.assertEqual(hc1.component.id, sc2.id)

        new_co_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)
        new_comp_node = Component.objects.get(name='node', prototype=new_co_proto)
        new_comp_node.delete()

        upgrade = setup.cook_upgrade(b2)
        cm.upgrade.do_upgrade(cluster, upgrade)
        hc2 = HostComponent.objects.get(cluster=cluster, service=co, component=sc1)
        self.assertEqual(hc2.component.id, sc1.id)
        r = HostComponent.objects.filter(cluster=cluster, service=co, component=sc2)
        self.assertEqual(len(r), 0)

    def test_component(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        b2 = setup.cook_cluster_bundle('2.0')
        sp = Prototype.objects.get(bundle=b2, type="service", name="hadoop")
        Component.objects.create(prototype=sp, name='data')
        setup.cook_cluster(b1, 'Test0')
        cluster = setup.cook_cluster(b1, 'Test1')

        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc11 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')
        self.assertEqual(sc11.component.prototype, co.prototype)

        sc12 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='node')
        self.assertEqual(sc12.component.prototype, co.prototype)

        new_co_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)
        cm.upgrade.switch_components(cluster, co, new_co_proto)

        new_comp1 = Component.objects.get(name='server', prototype=new_co_proto)
        sc21 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')
        self.assertEqual(sc11.id, sc21.id)
        self.assertEqual(sc21.component, new_comp1)
        new_comp2 = Component.objects.get(name='node', prototype=new_co_proto)
        sc22 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='node')
        self.assertEqual(sc12.id, sc22.id)
        self.assertEqual(sc22.component, new_comp2)

        new_comp3 = Component.objects.get(name='data', prototype=new_co_proto)
        sc23 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='data')
        self.assertEqual(sc23.component, new_comp3)

    def test_provider_upgrade(self):
        setup = SetUp()
        b1 = setup.cook_provider_bundle('1.0')
        b2 = setup.cook_provider_bundle('2.0')
        provider = setup.cook_provider(b1, "DF01")
        upgrade = setup.cook_upgrade(b2)

        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')

        try:
            r = cm.upgrade.do_upgrade(h1, upgrade)
            self.assertEqual(r, 'ok')
        except AdcmEx as e:
            self.assertEqual(e.code, 'UPGRADE_ERROR')
            self.assertEqual(e.msg, 'can upgrade only cluster or host provider')

        old_proto = Prototype.objects.get(type="host", name="DfHost", bundle=b1)
        new_proto = Prototype.objects.get(type="host", name="DfHost", bundle=b2)
        self.assertEqual(h1.prototype.id, old_proto.id)

        cm.upgrade.do_upgrade(provider, upgrade)
        h2 = Host.objects.get(provider=provider, fqdn='server01.inter.net')
        self.assertEqual(h1.id, h2.id)
        self.assertEqual(h2.prototype.id, new_proto.id)


class TestHC(TestCase):

    def test_action_hc_simple(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        cluster = setup.cook_cluster(b1, 'Test1')
        b2 = setup.cook_provider_bundle('1.0')
        provider = setup.cook_provider(b2, "DF01")
        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')

        action = Action(name="run")
        (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, [])
        self.assertEqual(hc_list, None)

        try:
            action = Action(name="run", hostcomponentmap=json.dumps("qwe"))
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, [])
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'TASK_ERROR')
            self.assertEqual(e.msg, 'hc is required')

        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')
        try:
            action = Action(name="run", hostcomponentmap=json.dumps("qwe"))
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": 500}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmApiEx as e:
            self.assertEqual(e.detail['code'], 'HOST_NOT_FOUND')

        try:
            action = Action(name="run", hostcomponentmap=json.dumps("qwe"))
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmApiEx as e:
            self.assertEqual(e.detail['code'], 'FOREIGN_HOST')

        cm.api.add_host_to_cluster(cluster, h1)
        try:
            action = Action(name="run", hostcomponentmap=json.dumps("qwe"))
            hc = [{"service_id": 500, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmApiEx as e:
            self.assertEqual(e.detail['code'], 'SERVICE_NOT_FOUND')

        try:
            action = Action(name="run", hostcomponentmap=json.dumps("qwe"))
            hc = [{"service_id": co.id, "component_id": 500, "host_id": h1.id}]
            (hc_list, _) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmApiEx as e:
            self.assertEqual(e.detail['code'], 'COMPONENT_NOT_FOUND')

    def test_action_hc(self):   # pylint: disable=too-many-locals
        setup = SetUp()
        b1 = setup.cook_cluster_bundle('1.0')
        cluster = setup.cook_cluster(b1, 'Test1')
        b2 = setup.cook_provider_bundle('1.0')
        provider = setup.cook_provider(b2, "DF01")

        h1 = Host.objects.get(provider=provider, fqdn='server01.inter.net')
        h2 = Host.objects.get(provider=provider, fqdn='server02.inter.net')
        co = ClusterObject.objects.get(cluster=cluster, prototype__name='hadoop')
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, component__name='server')

        cm.api.add_host_to_cluster(cluster, h1)
        cm.api.add_host_to_cluster(cluster, h2)

        try:
            act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'delete'}]
            action = Action(name="run", hostcomponentmap=json.dumps(act_hc))
            hc = [{"service_id": co.id, "component_id": sc1.id, "host_id": h1.id}]
            (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
            self.assertNotEqual(hc_list, None)
        except AdcmEx as e:
            self.assertEqual(e.code, 'WRONG_ACTION_HC')
            self.assertEqual(e.msg[:32], 'no permission to "add" component')

        act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'add'}]
        action = Action(name="run", hostcomponentmap=json.dumps(act_hc))
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h1.id},
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
        self.assertNotEqual(hc_list, None)
        self.assertEqual(delta['remove'], {})
        group = '{}.{}'.format(co.prototype.name, sc1.component.name)
        self.assertEqual(delta['add'][group]['server01.inter.net'], h1)
        self.assertEqual(delta['add'][group]['server02.inter.net'], h2)

        cm.api.save_hc(cluster, hc_list)
        act_hc = [{'service': 'hadoop', 'component': 'server', 'action': 'remove'}]
        action = Action(name="run", hostcomponentmap=json.dumps(act_hc))
        hc = [
            {"service_id": co.id, "component_id": sc1.id, "host_id": h2.id},
        ]
        (hc_list, delta) = cm.job.check_hostcomponentmap(cluster, action, hc)
        self.assertNotEqual(hc_list, None)
        self.assertEqual(delta['add'], {})
        group = '{}.{}'.format(co.prototype.name, sc1.component.name)
        self.assertEqual(delta['remove'][group]['server01.inter.net'], h1)
