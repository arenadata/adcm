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
from cm.upgrade import bundle_revert, check_upgrade, do_upgrade, switch_components

from adcm.tests.base import BaseTestCase


def cook_cluster_bundle(ver):
    bundle = Bundle.objects.create(name="ADH", version=ver)
    bundle.save()

    Prototype.objects.create(type="cluster", name="ADH", version=ver, bundle=bundle)
    sp2 = Prototype.objects.create(type="service", name="hive", bundle=bundle)

    Prototype.objects.create(parent=sp2, type="component", name="server", bundle=bundle)
    sp1 = Prototype.objects.create(type="service", name="hadoop", version=ver, bundle=bundle)

    Prototype.objects.create(parent=sp1, type="component", name="server", bundle=bundle)
    Prototype.objects.create(parent=sp1, type="component", name="node", bundle=bundle)

    return bundle


def cook_provider_bundle(ver):
    bundle = Bundle.objects.create(name="DF", version=ver)
    bundle.save()

    Prototype.objects.create(type="provider", name="DF", version=ver, bundle=bundle)
    Prototype.objects.create(type="host", name="DfHost", version=ver, bundle=bundle)

    return bundle


def cook_cluster(bundle, name):
    cluster_prototype = Prototype.objects.get(type="cluster", bundle=bundle)
    cluster = add_cluster(cluster_prototype, name)

    sp2 = Prototype.objects.get(type="service", name="hive", bundle=bundle)
    add_service_to_cluster(cluster, sp2)

    sp1 = Prototype.objects.get(type="service", name="hadoop", bundle=bundle)
    add_service_to_cluster(cluster, sp1)

    return cluster


def cook_provider(bundle, name):
    provider_prototype = Prototype.objects.get(type="provider", bundle=bundle)
    provider = add_host_provider(provider_prototype, name)
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")
    add_host(host_proto, provider, "server02.inter.net")
    add_host(host_proto, provider, "server01.inter.net")

    return provider


def cook_upgrade(bundle):
    return Upgrade.objects.create(bundle=bundle, min_version="1.0", max_version="2.0", state_available=["created"])


def get_config(obj):
    attr = {}
    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    if config_log.attr:
        attr = config_log.attr

    return config_log.config, attr


class TestUpgradeVersion(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.obj = gen_cluster()
        self.upgrade = self.cook_upgrade()

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
        success, msg = check_upgrade(obj, upgrade)

        self.assertEqual(success, result, f"check_upgrade msg: {msg or None}")

    def test_version(self):
        self.obj.prototype.version = "1.5"
        self.check_upgrade(self.obj, self.upgrade, True)

        self.obj.prototype.version = "2.5"
        self.check_upgrade(self.obj, self.upgrade, False)

        self.obj.prototype.version = "2.0"
        self.check_upgrade(self.obj, self.upgrade, True)

        self.obj.prototype.version = "1.0"
        self.check_upgrade(self.obj, self.upgrade, True)

    def test_strict_version(self):
        self.upgrade.min_strict = True
        self.upgrade.max_strict = True

        self.obj.prototype.version = "1.5"
        self.check_upgrade(self.obj, self.upgrade, True)

        self.obj.prototype.version = "2.5"
        self.check_upgrade(self.obj, self.upgrade, False)

        self.obj.prototype.version = "1.0"
        self.check_upgrade(self.obj, self.upgrade, False)

        self.obj.prototype.version = "2.0"
        self.check_upgrade(self.obj, self.upgrade, False)

    def test_state(self):
        self.upgrade.state_available = ["installed", "any"]
        self.obj.prototype.version = "1.5"

        self.obj.state = "created"
        self.check_upgrade(self.obj, self.upgrade, False)

        self.obj.state = "installed"
        self.check_upgrade(self.obj, self.upgrade, True)

    def test_issue(self):
        create_issue(self.obj, ConcernCause.CONFIG)

        self.check_upgrade(self.obj, self.upgrade, False)


class TestConfigUpgrade(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.add_conf = PrototypeConfig.objects.create

    @staticmethod
    def cook_proto():
        bundle = Bundle.objects.create(name="AD1", version="1.0")
        proto_1 = Prototype.objects.create(type="cluster", name="AD1", version="1.0", bundle=bundle)
        proto_2 = Prototype.objects.create(type="cluster", name="AD1", version="2.0", bundle=bundle)

        return proto_1, proto_2

    def test_empty_config(self):
        proto_1, proto_2 = self.cook_proto()
        cluster = add_cluster(proto_1, "Cluster1")

        self.assertEqual(cluster.config, None)

        switch_config(cluster, proto_2, proto_1)

        self.assertEqual(cluster.config, None)

    def test_empty_first_config(self):
        proto_1, proto_2 = self.cook_proto()
        self.add_conf(prototype=proto_2, name="port", type="integer", default=42)
        cluster = add_cluster(proto_1, "Cluster1")

        self.assertEqual(cluster.config, None)

        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config["port"], 42)

    def test_adding_parameter(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="port", type="integer", default=42)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})
        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"host": "arenadata.com", "port": 42})

    def test_deleting_parameter(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="port", type="integer", default=42)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 42})

    def test_default(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="port", type="integer", default=42)
        self.add_conf(prototype=proto_2, name="port", type="integer", default=43)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"port": 42})

        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 43})

    def test_non_default(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="port", type="integer", default=42)
        self.add_conf(prototype=proto_2, name="port", type="integer", default=43)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)
        old_conf["port"] = 100500
        save_obj_config(cluster.config, old_conf, {})
        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"port": 100500})

    def test_add_group(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="advance", type="group")
        self.add_conf(prototype=proto_2, name="advance", subname="port", type="integer", default=42)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto_2, proto_1)
        new_config, _ = get_config(cluster)

        self.assertEqual(new_config, {"host": "arenadata.com", "advance": {"port": 42}})

    def test_add_non_active_group(self):
        proto_1, proto_2 = self.cook_proto()

        # Old config with one key "host"
        self.add_conf(prototype=proto_1, name="host", type="string", default="arenadata.com")

        # New config with key "host" and activatable group "advance"
        self.add_conf(prototype=proto_2, name="host", type="string", default="arenadata.com")
        limits = {"activatable": True, "active": False}
        self.add_conf(prototype=proto_2, name="advance", type="group", limits=limits)
        self.add_conf(prototype=proto_2, name="advance", subname="port", type="integer", default=42)

        # Create cluster with old config
        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)
        self.assertEqual(old_conf, {"host": "arenadata.com"})

        # Upgrade
        switch_config(cluster, proto_2, proto_1)
        new_config, new_attr = get_config(cluster)

        # Check that new activatable but inactive group default values are added to new config
        self.assertEqual(new_config, {"host": "arenadata.com", "advance": {"port": 42}})
        self.assertEqual(new_attr, {"advance": {"active": False}})

    def test_add_active_group(self):
        proto_1, proto_2 = self.cook_proto()

        self.add_conf(prototype=proto_1, name="host", type="string", default="arenadata.com")
        self.add_conf(prototype=proto_2, name="host", type="string", default="arenadata.com")
        limits = {"activatable": True, "active": True}
        self.add_conf(prototype=proto_2, name="advance", type="group", limits=limits)
        self.add_conf(prototype=proto_2, name="advance", subname="port", type="integer", default=42)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, _ = get_config(cluster)

        self.assertEqual(old_conf, {"host": "arenadata.com"})

        switch_config(cluster, proto_2, proto_1)
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

        proto_1, proto_2 = self.cook_proto()
        self.add_conf(
            prototype=proto_1,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto_1, name="advance", subname="port", type="integer", default=11)

        self.add_conf(
            prototype=proto_2,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto_2, name="advance", subname="port", type="integer", default=22)
        cluster = add_cluster(proto_1, "Cluster1")
        update_obj_config(cluster.config, {"advance": {"port": 33}}, {"advance": {"active": True}})
        old_conf, old_attr = get_config(cluster)

        self.assertEqual(old_conf, {"advance": {"port": 33}})
        self.assertEqual(old_attr, {"advance": {"active": True}})

        switch_config(cluster, proto_2, proto_1)
        new_conf, new_attr = get_config(cluster)

        self.assertEqual(new_conf, {"advance": {"port": 33}})
        self.assertEqual(new_attr, {"advance": {"active": True}})

    def test_non_active_group(self):
        proto_1, proto_2 = self.cook_proto()

        # Old config with activatable group "advance"
        self.add_conf(
            prototype=proto_1,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto_1, name="advance", subname="port", type="integer", default=11)

        # New config with the same activatable group "advance"
        self.add_conf(
            prototype=proto_2,
            name="advance",
            type="group",
            limits={"activatable": True, "active": False},
        )
        self.add_conf(prototype=proto_2, name="advance", subname="port", type="integer", default=11)

        cluster = add_cluster(proto_1, "Cluster1")
        old_conf, old_attr = get_config(cluster)

        self.assertEqual(old_conf, {"advance": {"port": 11}})
        self.assertEqual(old_attr, {"advance": {"active": False}})

        # Upgrade
        switch_config(cluster, proto_2, proto_1)
        new_conf, new_attr = get_config(cluster)

        # Check that activatable but not active group does not disappear from new config
        self.assertEqual(new_conf, {"advance": {"port": 11}})
        self.assertEqual(new_attr, {"advance": {"active": False}})


class TestUpgrade(BaseTestCase):
    def test_upgrade_with_license(self):
        bundle_1 = cook_cluster_bundle("1.0")
        bundle_2 = cook_cluster_bundle("2.0")
        cluster = cook_cluster(bundle_1, "Test1")
        upgrade = cook_upgrade(bundle_2)

        license_hash_1 = "36e8d9f836e8ddc797f6e1b39bc856da8ab14da201258125175f5b9180f69304"
        license_hash_2 = "9dbd1b5494fd6040863339dece1306358d4f0f16f8246086b05c2f32886ae5ef"
        old_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_1)
        old_proto.license = "unaccepted"
        old_proto.license_hash = license_hash_1
        old_proto.save(update_fields=["license", "license_hash"])
        with self.assertRaisesRegex(AdcmEx, 'License for prototype "hadoop" service 1.0 is not accepted'):
            do_upgrade(cluster, upgrade, {}, {}, [])

        old_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_1)
        new_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_2)
        old_proto.license = "accepted"
        new_proto.license = "unaccepted"
        new_proto.license_hash = license_hash_2
        old_proto.save(update_fields=["license"])
        new_proto.save(update_fields=["license", "license_hash"])
        with self.assertRaisesRegex(AdcmEx, 'License for prototype "hadoop" service 2.0 is not accepted'):
            do_upgrade(cluster, upgrade, {}, {}, [])

        new_proto.license = "accepted"
        new_proto.save(update_fields=["license"])
        do_upgrade(cluster, upgrade, {}, {}, [])

    def test_cluster_upgrade(self):
        bundle_1 = cook_cluster_bundle("1.0")
        bundle_2 = cook_cluster_bundle("2.0")
        cook_cluster(bundle_1, "Test0")
        cluster = cook_cluster(bundle_1, "Test1")
        upgrade = cook_upgrade(bundle_2)

        service_1 = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")

        try:
            result = do_upgrade(service_1, upgrade, {}, {}, [])

            self.assertEqual(result, "ok")
        except AdcmEx as e:
            self.assertEqual(e.code, "UPGRADE_ERROR")
            self.assertEqual(e.msg, "can upgrade only cluster or host provider")

        old_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_1)
        new_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_2)

        self.assertEqual(service_1.prototype.id, old_proto.id)

        do_upgrade(cluster, upgrade, {}, {}, [])
        service_2 = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")

        self.assertEqual(service_1.id, service_2.id)
        self.assertEqual(service_2.prototype.id, new_proto.id)

    def test_hc(self):  # pylint: disable=too-many-locals
        bundle_1 = cook_cluster_bundle("1.0")
        bundle_2 = cook_cluster_bundle("2.0")
        bundle_3 = cook_provider_bundle("1.0")

        cluster = cook_cluster(bundle_1, "Test1")
        provider = cook_provider(bundle_3, "DF01")

        service = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        service_component_1 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="server")
        service_component_2 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="node")
        host_1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        host_2 = Host.objects.get(provider=provider, fqdn="server02.inter.net")
        add_host_to_cluster(cluster, host_1)
        add_host_to_cluster(cluster, host_2)

        host_component = [
            {"service_id": service.id, "host_id": host_1.id, "component_id": service_component_1.id},
            {"service_id": service.id, "host_id": host_2.id, "component_id": service_component_2.id},
        ]
        add_hc(cluster, host_component)
        host_component_1 = HostComponent.objects.get(cluster=cluster, service=service, component=service_component_2)

        self.assertEqual(host_component_1.component.id, service_component_2.id)

        new_service_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_2)
        new_component_node = Prototype.objects.get(name="node", type="component", parent=new_service_proto)
        new_component_node.delete()

        upgrade = cook_upgrade(bundle_2)
        do_upgrade(obj=cluster, upgrade=upgrade, config={}, attr={}, hostcomponent=[])
        host_component_2 = HostComponent.objects.get(cluster=cluster, service=service, component=service_component_1)

        self.assertEqual(host_component_2.component.id, service_component_1.id)
        host_components = HostComponent.objects.filter(cluster=cluster, service=service, component=service_component_2)

        self.assertEqual(len(host_components), 0)

    def test_component(self):  # pylint: disable=too-many-locals
        bundle_1 = cook_cluster_bundle("1.0")
        bundle_2 = cook_cluster_bundle("2.0")
        service_prototype = Prototype.objects.get(bundle=bundle_2, type="service", name="hadoop")
        Prototype.objects.create(parent=service_prototype, type="component", name="data", bundle=bundle_2)
        cook_cluster(bundle_1, "Test0")
        cluster = cook_cluster(bundle_1, "Test1")

        service = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        service_component_11 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="server")

        self.assertEqual(service_component_11.prototype.parent, service.prototype)

        service_component_12 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="node")

        self.assertEqual(service_component_12.prototype.parent, service.prototype)

        new_service_proto = Prototype.objects.get(type="service", name="hadoop", bundle=bundle_2)
        switch_components(cluster, service, new_service_proto)

        new_component_prototype_1 = Prototype.objects.get(name="server", type="component", parent=new_service_proto)
        service_component_21 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="server")

        self.assertEqual(service_component_11.id, service_component_21.id)
        self.assertEqual(service_component_21.prototype, new_component_prototype_1)

        new_component_prototype_2 = Prototype.objects.get(name="node", type="component", parent=new_service_proto)
        service_component_22 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="node")

        self.assertEqual(service_component_12.id, service_component_22.id)
        self.assertEqual(service_component_22.prototype, new_component_prototype_2)

        new_component_prototype_3 = Prototype.objects.get(name="data", type="component", parent=new_service_proto)
        service_component_23 = ServiceComponent.objects.get(cluster=cluster, service=service, prototype__name="data")

        self.assertEqual(service_component_23.prototype, new_component_prototype_3)

    def test_provider_upgrade(self):
        bundle_1 = cook_provider_bundle("1.0")
        bundle_2 = cook_provider_bundle("2.0")
        provider = cook_provider(bundle_1, "DF01")
        upgrade = cook_upgrade(bundle_2)

        host_1 = Host.objects.get(provider=provider, fqdn="server01.inter.net")

        try:
            result = do_upgrade(host_1, upgrade, {}, {}, [])

            self.assertEqual(result, "ok")
        except AdcmEx as e:
            self.assertEqual(e.code, "UPGRADE_ERROR")
            self.assertEqual(e.msg, "can upgrade only cluster or host provider")

        old_proto = Prototype.objects.get(type="host", name="DfHost", bundle=bundle_1)
        new_proto = Prototype.objects.get(type="host", name="DfHost", bundle=bundle_2)

        self.assertEqual(host_1.prototype.id, old_proto.id)

        do_upgrade(provider, upgrade, {}, {}, [])
        host_2 = Host.objects.get(provider=provider, fqdn="server01.inter.net")

        self.assertEqual(host_1.id, host_2.id)
        self.assertEqual(host_2.prototype.id, new_proto.id)


class TestRevertUpgrade(BaseTestCase):
    def test_simple_revert_upgrade(self):  # pylint: disable=too-many-locals
        bundle1 = cook_cluster_bundle(ver="1.0")
        bundle2 = cook_cluster_bundle(ver="2.0")
        service1_proto1 = Prototype.objects.get(bundle=bundle1, type="service", name="hadoop")
        service1_proto2 = Prototype.objects.get(bundle=bundle2, type="service", name="hadoop")

        service2_proto1 = Prototype.objects.get(bundle=bundle1, type="service", name="hive")
        service2_proto2 = Prototype.objects.get(bundle=bundle2, type="service", name="hive")

        component11_proto1 = Prototype.objects.get(
            bundle=bundle1,
            type="component",
            name="server",
            parent=service1_proto1,
        )
        component11_proto2 = Prototype.objects.get(
            bundle=bundle2,
            type="component",
            name="server",
            parent=service1_proto2,
        )

        component12_proto1 = Prototype.objects.get(
            bundle=bundle1,
            type="component",
            name="node",
            parent=service1_proto1,
        )
        component12_proto2 = Prototype.objects.get(
            bundle=bundle2,
            type="component",
            name="node",
            parent=service1_proto2,
        )

        component21_proto1 = Prototype.objects.get(
            bundle=bundle1,
            type="component",
            name="server",
            parent=service2_proto1,
        )
        component21_proto2 = Prototype.objects.get(
            bundle=bundle2,
            type="component",
            name="server",
            parent=service2_proto2,
        )

        cluster = cook_cluster(bundle=bundle1, name="Test0")
        upgrade = cook_upgrade(bundle=bundle2)

        service_1 = ClusterObject.objects.get(cluster=cluster, prototype__name="hadoop")
        service_2 = ClusterObject.objects.get(cluster=cluster, prototype__name="hive")
        comp_11 = ServiceComponent.objects.get(cluster=cluster, service=service_1, prototype__name="server")
        comp_12 = ServiceComponent.objects.get(cluster=cluster, service=service_1, prototype__name="node")
        comp_21 = ServiceComponent.objects.get(cluster=cluster, service=service_2, prototype__name="server")

        self.assertEqual(service_1.prototype, service1_proto1)
        self.assertEqual(service_2.prototype, service2_proto1)
        self.assertEqual(comp_11.prototype, component11_proto1)
        self.assertEqual(comp_12.prototype, component12_proto1)
        self.assertEqual(comp_21.prototype, component21_proto1)

        do_upgrade(obj=cluster, upgrade=upgrade, config={}, attr={}, hostcomponent=[])

        service_1.refresh_from_db()
        service_2.refresh_from_db()
        comp_11.refresh_from_db()
        comp_12.refresh_from_db()
        comp_21.refresh_from_db()

        self.assertEqual(service_1.prototype, service1_proto2)
        self.assertEqual(service_2.prototype, service2_proto2)
        self.assertEqual(comp_11.prototype, component11_proto2)
        self.assertEqual(comp_12.prototype, component12_proto2)
        self.assertEqual(comp_21.prototype, component21_proto2)

        bundle_revert(obj=cluster)

        service_1.refresh_from_db()
        service_2.refresh_from_db()
        comp_11.refresh_from_db()
        comp_12.refresh_from_db()
        comp_21.refresh_from_db()

        self.assertEqual(service_1.prototype, service1_proto1)
        self.assertEqual(service_2.prototype, service2_proto1)
        self.assertEqual(comp_11.prototype, component11_proto1)
        self.assertEqual(comp_12.prototype, component12_proto1)
        self.assertEqual(comp_21.prototype, component21_proto1)

    def test_provider_revert(self):
        bundle1 = cook_provider_bundle(ver="1.0")
        bundle2 = cook_provider_bundle(ver="2.0")
        provider = cook_provider(bundle=bundle1, name="DF01")
        upgrade = cook_upgrade(bundle=bundle2)

        host = Host.objects.get(provider=provider, fqdn="server01.inter.net")
        host_proto1 = Prototype.objects.get(type="host", name="DfHost", bundle=bundle1)
        host_proto2 = Prototype.objects.get(type="host", name="DfHost", bundle=bundle2)
        provider_proto1 = Prototype.objects.get(type="provider", bundle=bundle1)
        provider_proto2 = Prototype.objects.get(type="provider", bundle=bundle2)

        self.assertEqual(host.prototype, host_proto1)
        self.assertEqual(provider.prototype, provider_proto1)

        do_upgrade(obj=provider, upgrade=upgrade, config={}, attr={}, hostcomponent=[])

        provider.refresh_from_db()
        host.refresh_from_db()

        self.assertEqual(host.prototype, host_proto2)
        self.assertEqual(provider.prototype, provider_proto2)

        bundle_revert(obj=provider)

        provider.refresh_from_db()
        host.refresh_from_db()

        self.assertEqual(host.prototype, host_proto1)
        self.assertEqual(provider.prototype, provider_proto1)
