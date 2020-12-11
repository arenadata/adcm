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

import cm.api
import cm.job
from cm.models import Cluster, Host, ClusterObject, ServiceComponent, HostComponent
from cm.models import Bundle, Upgrade, Prototype, Component, PrototypeConfig, ConfigLog
from cm.errors import AdcmEx
from cm import adcm_config


class TestUpgradeVersion(TestCase):

    def cook_cluster(self):
        b = Bundle(name="ADH", version="1.0")
        proto = Prototype(type="cluster", name="ADH", bundle=b)
        return Cluster(prototype=proto, issue={})

    def cook_upgrade(self):
        return Upgrade(
            min_version="1.0",
            max_version="2.0",
            min_strict=False,
            max_strict=False,
            state_available='any'
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
        upgrade.state_available = ["installed", "any"]
        obj.prototype.version = "1.5"

        obj.state = "created"
        self.check_upgrade(obj, upgrade, False)

        obj.state = "installed"
        self.check_upgrade(obj, upgrade, True)

    def test_issue(self):
        obj = self.cook_cluster()
        obj.issue = {"config": False}
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
            state_available=['created']
        )


def get_config(obj):
    attr = {}
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    if cl.attr:
        attr = cl.attr
    return cl.config, attr


class TestConfigUpgrade(TestCase):
    add_conf = PrototypeConfig.objects.create

    def cook_proto(self):
        b = Bundle.objects.create(name='AD1', version='1.0')
        proto1 = Prototype.objects.create(type="cluster", name="AD1", version="1.0", bundle=b)
        proto2 = Prototype.objects.create(type="cluster", name="AD1", version="2.0", bundle=b)
        return (proto1, proto2)

    def test_empty_config(self):
        (proto1, proto2) = self.cook_proto()
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        self.assertEqual(cluster.config, None)
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        self.assertEqual(cluster.config, None)

    def test_empty_first_config(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto2, name='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        self.assertEqual(cluster.config, None)
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config['port'], 42)

    def test_adding_parameter(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'host': 'arenadata.com'})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config, {'host': 'arenadata.com', 'port': 42})

    def test_deleting_parameter(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'host': 'arenadata.com'})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config, {'port': 42})

    def test_default(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='port', type='integer', default=42)
        self.add_conf(prototype=proto2, name='port', type='integer', default=43)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'port': 42})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config, {'port': 43})

    def test_non_default(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='port', type='integer', default=42)
        self.add_conf(prototype=proto2, name='port', type='integer', default=43)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        old_conf['port'] = 100500
        cm.adcm_config.save_obj_config(cluster.config, old_conf, {})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config, {'port': 100500})

    def test_add_group(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='advance', type='group')
        self.add_conf(prototype=proto2, name='advance', subname='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'host': 'arenadata.com'})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)
        self.assertEqual(new_config, {'host': 'arenadata.com', 'advance': {'port': 42}})

    def test_add_non_active_group(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='host', type='string', default='arenadata.com')
        limits = {"activatable": True, "active": False}
        self.add_conf(prototype=proto2, name='advance', type='group', limits=limits)
        self.add_conf(prototype=proto2, name='advance', subname='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'host': 'arenadata.com'})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, new_attr = get_config(cluster)
        self.assertEqual(new_config, {'host': 'arenadata.com', 'advance': None})
        self.assertEqual(new_attr, {'advance': {'active': False}})

    def test_add_active_group(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name='host', type='string', default='arenadata.com')
        self.add_conf(prototype=proto2, name='host', type='string', default='arenadata.com')
        limits = {"activatable": True, "active": True}
        self.add_conf(prototype=proto2, name='advance', type='group', limits=limits)
        self.add_conf(prototype=proto2, name='advance', subname='port', type='integer', default=42)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {'host': 'arenadata.com'})
        cm.adcm_config.switch_config(cluster, proto2, proto1)
        new_config, new_attr = get_config(cluster)
        self.assertEqual(new_config, {'host': 'arenadata.com', 'advance': {'port': 42}})
        self.assertEqual(new_attr, {'advance': {'active': True}})

    def test_from_active_group_to_not_active_group(self):
        """Scenario:
        * Create prototype1 with activatable group, active=False
        * Create prototype2 with activatable group, active=False
        * Create cluster from prototype1
        * Update cluster config, activate group, set value
        * Update cluster config from prototype2
        * Expect that the cluster configuration has not changed
        """
        proto1, proto2 = self.cook_proto()
        self.add_conf(prototype=proto1, name='advance', type='group',
                      limits={"activatable": True, "active": False})
        self.add_conf(prototype=proto1, name='advance', subname='port', type='integer', default=11)

        self.add_conf(prototype=proto2, name='advance', type='group',
                      limits={"activatable": True, "active": False})
        self.add_conf(prototype=proto2, name='advance', subname='port', type='integer', default=22)
        cluster = cm.api.add_cluster(proto1, 'Cluster1')
        cm.api.update_obj_config(
            cluster.config, {'advance': {'port': 33}}, {'advance': {'active': True}}
        )
        old_conf, old_attr = get_config(cluster)
        self.assertEqual(old_conf, {'advance': {'port': 33}})
        self.assertEqual(old_attr, {'advance': {'active': True}})
        adcm_config.switch_config(cluster, proto2, proto1)
        new_conf, new_attr = get_config(cluster)
        self.assertEqual(new_conf, {'advance': {'port': 33}})
        self.assertEqual(new_attr, {'advance': {'active': True}})


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
