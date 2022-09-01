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

from cm.adcm_config import save_obj_config, switch_config
from cm.api import (
    add_cluster,
    add_hc,
    add_host,
    add_host_provider,
    add_host_to_cluster,
    add_service_to_cluster,
    update_obj_config,
)
from cm.errors import AdcmEx
from cm.issue import create_issue
from cm.models import (
    Bundle,
    ClusterObject,
    ConcernCause,
    ConfigLog,
    Host,
    HostComponent,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
    Upgrade,
)
from cm.tests.utils import gen_cluster
from cm.upgrade import check_upgrade, do_upgrade, switch_components


def cook_cluster_bundle(ver):
    b = Bundle.objects.create(name="ADH", version=ver)
    b.save()
    Prototype.objects.create(type="cluster", name="ADH", version=ver, bundle=b)
    sp2 = Prototype.objects.create(type="service", name="hive", bundle=b)
    Prototype.objects.create(parent=sp2, type="component", name="server", bundle=b)
    sp1 = Prototype.objects.create(type="service", name="hadoop", version=ver, bundle=b)
    Prototype.objects.create(parent=sp1, type="component", name="server", bundle=b)
    Prototype.objects.create(parent=sp1, type="component", name="node", bundle=b)

    return b


def cook_provider_bundle(ver):
    b = Bundle.objects.create(name="DF", version=ver)
    b.save()
    Prototype.objects.create(type="provider", name="DF", version=ver, bundle=b)
    Prototype.objects.create(type="host", name="DfHost", version=ver, bundle=b)

    return b


def cook_cluster(bundle, name):
    cp = Prototype.objects.get(type="cluster", bundle=bundle)
    cluster = add_cluster(cp, name)
    sp2 = Prototype.objects.get(type="service", name="hive", bundle=bundle)
    add_service_to_cluster(cluster, sp2)
    sp1 = Prototype.objects.get(type="service", name="hadoop", bundle=bundle)
    add_service_to_cluster(cluster, sp1)

    return cluster


def cook_provider(bundle, name):
    pp = Prototype.objects.get(type="provider", bundle=bundle)
    provider = add_host_provider(pp, name)
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")
    add_host(host_proto, provider, "server02.inter.net")
    add_host(host_proto, provider, "server01.inter.net")

    return provider


def cook_upgrade(bundle):
    return Upgrade.objects.create(
        bundle=bundle, min_version="1.0", max_version="2.0", state_available=["created"]
    )


def get_config(obj):
    attr = {}
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    if cl.attr:
        attr = cl.attr

    return cl.config, attr


class TestUpgradeVersion(TestCase):
    @staticmethod
    def cook_upgrade():
        return Upgrade(
            min_version="1.0",
            max_version="2.0",
            min_strict=False,
            max_strict=False,
            state_available="any",
        )

    def check_upgrade(self, obj, upgrade, result):
        ok, msg = check_upgrade(obj, upgrade)
        self.assertEqual(ok, result, f"check_upgrade msg: {msg or None}")

    def test_version(self):
        obj = gen_cluster()
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
        obj = gen_cluster()
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
        obj = gen_cluster()
        upgrade = self.cook_upgrade()
        upgrade.state_available = ["installed", "any"]
        obj.prototype.version = "1.5"

        obj.state = "created"
        self.check_upgrade(obj, upgrade, False)

        obj.state = "installed"
        self.check_upgrade(obj, upgrade, True)

    def test_issue(self):
        obj = gen_cluster()
        create_issue(obj, ConcernCause.Config)
        upgrade = self.cook_upgrade()

        self.check_upgrade(obj, upgrade, False)


class TestConfigUpgrade(TestCase):
    add_conf = PrototypeConfig.objects.create

    @staticmethod
    def cook_proto():
        b = Bundle.objects.create(name="AD1", version="1.0")
        proto1 = Prototype.objects.create(type="cluster", name="AD1", version="1.0", bundle=b)
        proto2 = Prototype.objects.create(type="cluster", name="AD1", version="2.0", bundle=b)
        return proto1, proto2

    def test_empty_config(self):
        (proto1, proto2) = self.cook_proto()
        cluster = add_cluster(proto1, "Cluster1")

        self.assertEqual(cluster.config, None)

        switch_config(cluster, proto2, proto1)

        self.assertEqual(cluster.config, None)

    def test_empty_first_config(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto2, name="port", type="integer", default=42)
        cluster = add_cluster(proto1, "Cluster1")

        self.assertEqual(cluster.config, None)

        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config["port"], 42)

    def test_adding_parameter(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="port", type="integer", default=42)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})
        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"host": "arenadata.com", "port": 42})

    def test_deleting_parameter(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="port", type="integer", default=42)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 42})

    def test_default(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name="port", type="integer", default=42)
        self.add_conf(prototype=proto2, name="port", type="integer", default=43)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"port": 42})

        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 43})

    def test_non_default(self):
        proto1, proto2 = self.cook_proto()
        self.add_conf(prototype=proto1, name="port", type="integer", default=42)
        self.add_conf(prototype=proto2, name="port", type="integer", default=43)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)
        old_conf["port"] = 100500
        save_obj_config(cluster.config, old_conf, {})
        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 100500})

    def test_add_group(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="advance", type="group")
        self.add_conf(prototype=proto2, name="advance", subname="port", type="integer", default=42)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto2, proto1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"host": "arenadata.com", "advance": {"port": 42}})

    def test_add_non_active_group(self):
        (proto1, proto2) = self.cook_proto()
        # Old config with one key "host"
        self.add_conf(prototype=proto1, name="host", type="string", default="arenadata.com")

        # New config with key "host" and activatable group "advance"
        self.add_conf(prototype=proto2, name="host", type="string", default="arenadata.com")
        limits = {"activatable": True, "active": False}
        self.add_conf(prototype=proto2, name="advance", type="group", limits=limits)
        self.add_conf(prototype=proto2, name="advance", subname="port", type="integer", default=42)

        # Create cluster with old config
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {"host": "arenadata.com"})

        # Upgrade
        switch_config(cluster, proto2, proto1)
        new_config, new_attr = get_config(cluster)

        # Check that new activatable but inactive group default values are added to new config
        self.assertEqual(new_config, {"host": "arenadata.com", "advance": {"port": 42}})
        self.assertEqual(new_attr, {"advance": {"active": False}})

    def test_add_active_group(self):
        (proto1, proto2) = self.cook_proto()
        self.add_conf(prototype=proto1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto2, name="host", type="string", default="arenadata.com")
        limits = {"activatable": True, "active": True}
        self.add_conf(prototype=proto2, name="advance", type="group", limits=limits)
        self.add_conf(prototype=proto2, name="advance", subname="port", type="integer", default=42)
        cluster = add_cluster(proto1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto2, proto1)
        new_config, new_attr = get_config(cluster)

        self.assertEqual(new_config, {"host": "arenadata.com", "advance": {"port": 42}})
        self.assertEqual(new_attr, {"advance": {"active": True}})

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
        self.add_conf(
            prototype=proto1,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto1, name="advance", subname="port", type="integer", default=11)

        self.add_conf(
            prototype=proto2,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto2, name="advance", subname="port", type="integer", default=22)
        cluster = add_cluster(proto1, "Cluster1")
        update_obj_config(cluster.config, {"advance": {"port": 33}}, {"advance": {"active": True}})
        old_conf, old_attr = get_config(cluster)

        self.assertEqual(old_conf, {"advance": {"port": 33}})
        self.assertEqual(old_attr, {"advance": {"active": True}})

        switch_config(cluster, proto2, proto1)
        new_conf, new_attr = get_config(cluster)

        self.assertEqual(new_conf, {"advance": {"port": 33}})
        self.assertEqual(new_attr, {"advance": {"active": True}})

    def test_non_active_group(self):
        proto1, proto2 = self.cook_proto()
        # Old config with activatable group "advance"
        self.add_conf(
            prototype=proto1,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto1, name="advance", subname="port", type="integer", default=11)

        # New config with the same activatable group "advance"
        self.add_conf(
            prototype=proto2,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto2, name="advance", subname="port", type="integer", default=11)

        cluster = add_cluster(proto1, "Cluster1")
        old_conf, old_attr = get_config(cluster)

        self.assertEqual(old_conf, {"advance": {"port": 11}})
        self.assertEqual(old_attr, {"advance": {"active": False}})

        # Upgrade
        switch_config(cluster, proto2, proto1)
        new_conf, new_attr = get_config(cluster)

        # Check that activatable but not active group does not disappear from new config
        self.assertEqual(new_conf, {"advance": {"port": 11}})
        self.assertEqual(new_attr, {"advance": {"active": False}})


class TestUpgrade(TestCase):
    def test_cluster_upgrade(self):
        b1 = cook_cluster_bundle("1.0")
        b2 = cook_cluster_bundle("2.0")
        cook_cluster(b1, "Test0")
        cluster = cook_cluster(b1, "Test1")
        upgrade = cook_upgrade(b2)

        co1 = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")

        try:
            r = do_upgrade(co1, upgrade, {}, {}, [])

            self.assertEqual(r, "ok")
        except AdcmEx as e:
            self.assertEqual(e.code, "UPGRADE_ERROR")
            self.assertEqual(e.msg, "can upgrade only cluster or host provider")

        old_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b1)
        new_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)

        self.assertEqual(co1.prototype.id, old_proto.id)

        do_upgrade(cluster, upgrade, {}, {}, [])
        co2 = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")

        self.assertEqual(co1.id, co2.id)
        self.assertEqual(co2.prototype.id, new_proto.id)

    def test_hc(self):  # pylint: disable=too-many-locals
        b1 = cook_cluster_bundle("1.0")
        b2 = cook_cluster_bundle("2.0")
        b3 = cook_provider_bundle("1.0")

        cluster = cook_cluster(b1, "Test1")
        provider = cook_provider(b3, "DF01")

        co = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc1 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="server")
        sc2 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="node")
        h1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        h2 = Host.objects.get(provider=provider, fqdn="server02.inter.net")
        add_host_to_cluster(cluster, h1)
        add_host_to_cluster(cluster, h2)

        hc = [
            {"service_id": co.id, "host_id": h1.id, "component_id": sc1.id},
            {"service_id": co.id, "host_id": h2.id, "component_id": sc2.id},
        ]
        add_hc(cluster, hc)
        hc1 = HostComponent.objects.get(cluster=cluster, service=co, component=sc2)

        self.assertEqual(hc1.component.id, sc2.id)

        new_co_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)
        new_comp_node = Prototype.objects.get(name="node", type="component", parent=new_co_proto)
        new_comp_node.delete()

        upgrade = cook_upgrade(b2)
        do_upgrade(cluster, upgrade, {}, {}, [])
        hc2 = HostComponent.objects.get(cluster=cluster, service=co, component=sc1)

        self.assertEqual(hc2.component.id, sc1.id)
        r = HostComponent.objects.filter(cluster=cluster, service=co, component=sc2)

        self.assertEqual(len(r), 0)

    def test_component(self):  # pylint: disable=too-many-locals
        b1 = cook_cluster_bundle("1.0")
        b2 = cook_cluster_bundle("2.0")
        sp = Prototype.objects.get(bundle=b2, type="service", name="hadoop")
        Prototype.objects.create(parent=sp, type="component", name="data", bundle=b2)
        cook_cluster(b1, "Test0")
        cluster = cook_cluster(b1, "Test1")

        co = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        sc11 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="server")

        self.assertEqual(sc11.prototype.parent, co.prototype)

        sc12 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="node")

        self.assertEqual(sc12.prototype.parent, co.prototype)

        new_co_proto = Prototype.objects.get(type="service", name="hadoop", bundle=b2)
        switch_components(cluster, co, new_co_proto)

        new_comp1 = Prototype.objects.get(name="server", type="component", parent=new_co_proto)
        sc21 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="server")

        self.assertEqual(sc11.id, sc21.id)
        self.assertEqual(sc21.prototype, new_comp1)

        new_comp2 = Prototype.objects.get(name="node", type="component", parent=new_co_proto)
        sc22 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="node")

        self.assertEqual(sc12.id, sc22.id)
        self.assertEqual(sc22.prototype, new_comp2)

        new_comp3 = Prototype.objects.get(name="data", type="component", parent=new_co_proto)
        sc23 = ServiceComponent.objects.get(cluster=cluster, service=co, prototype__name="data")

        self.assertEqual(sc23.prototype, new_comp3)

    def test_provider_upgrade(self):
        b1 = cook_provider_bundle("1.0")
        b2 = cook_provider_bundle("2.0")
        provider = cook_provider(b1, "DF01")
        upgrade = cook_upgrade(b2)

        h1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")

        try:
            r = do_upgrade(h1, upgrade, {}, {}, [])

            self.assertEqual(r, "ok")
        except AdcmEx as e:
            self.assertEqual(e.code, "UPGRADE_ERROR")
            self.assertEqual(e.msg, "can upgrade only cluster or host provider")

        old_proto = Prototype.objects.get(type="host", name="DfHost", bundle=b1)
        new_proto = Prototype.objects.get(type="host", name="DfHost", bundle=b2)

        self.assertEqual(h1.prototype.id, old_proto.id)

        do_upgrade(provider, upgrade, {}, {}, [])
        h2 = Host.objects.get(provider=provider, fqdn="server01.inter.net")

        self.assertEqual(h1.id, h2.id)
        self.assertEqual(h2.prototype.id, new_proto.id)
