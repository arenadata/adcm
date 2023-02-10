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

import functools
from typing import List, Tuple, Union

from cm.adcm_config import (
    init_object_config,
    make_object_config,
    obj_ref,
    proto_ref,
    save_obj_config,
    switch_config,
)
from cm.api import (
    add_components_to_service,
    add_service_to_cluster,
    check_license,
    save_hc,
    version_in,
)
from cm.errors import raise_adcm_ex
from cm.issue import update_hierarchy_issues
from cm.job import start_task
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    Prototype,
    PrototypeImport,
    ServiceComponent,
    Upgrade,
)
from cm.status_api import post_event
from django.db import transaction
from rbac.models import re_apply_object_policy
from version_utils import rpm


def switch_object(obj: Host | ClusterObject, new_prototype: Prototype) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))
    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])
    switch_config(obj=obj, new_proto=new_prototype, old_proto=old_prototype)


def switch_services(upgrade: Upgrade, cluster: Cluster) -> None:
    for service in ClusterObject.objects.filter(cluster=cluster):
        check_license(service.prototype)
        try:
            new_prototype = Prototype.objects.get(bundle=upgrade.bundle, type="service", name=service.prototype.name)
            check_license(new_prototype)
            switch_object(service, new_prototype)
            switch_components(cluster, service, new_prototype)
        except Prototype.DoesNotExist:
            service.delete()

    switch_hc(cluster, upgrade)


def switch_components(cluster: Cluster, service: ClusterObject, new_co_proto: Prototype) -> None:
    for comp in ServiceComponent.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(parent=new_co_proto, type="component", name=comp.prototype.name)
            switch_object(obj=comp, new_prototype=new_comp_prototype)
        except Prototype.DoesNotExist:
            comp.delete()

    for comp_proto in Prototype.objects.filter(parent=new_co_proto, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": comp_proto}
        if not ServiceComponent.objects.filter(**kwargs).exists():
            comp = ServiceComponent.objects.create(**kwargs)
            make_object_config(obj=comp, prototype=comp_proto)


def switch_hosts(upgrade: Upgrade, provider: HostProvider) -> None:
    for prototype in Prototype.objects.filter(bundle=upgrade.bundle, type="host"):
        for host in Host.objects.filter(provider=provider, prototype__name=prototype.name):
            switch_object(host, prototype)


def check_upgrade_version(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    proto = obj.prototype
    if upgrade.min_strict:
        if rpm.compare_versions(proto.version, upgrade.min_version) <= 0:
            msg = "{} version {} is less than or equal to upgrade min version {}"

            return False, msg.format(proto.type, proto.version, upgrade.min_version)
    else:
        if rpm.compare_versions(proto.version, upgrade.min_version) < 0:
            msg = "{} version {} is less than upgrade min version {}"

            return False, msg.format(proto.type, proto.version, upgrade.min_version)

    if upgrade.max_strict:
        if rpm.compare_versions(proto.version, upgrade.max_version) >= 0:
            msg = "{} version {} is more than or equal to upgrade max version {}"

            return False, msg.format(proto.type, proto.version, upgrade.max_version)
    else:
        if rpm.compare_versions(proto.version, upgrade.max_version) > 0:
            msg = "{} version {} is more than upgrade max version {}"

            return False, msg.format(proto.type, proto.version, upgrade.max_version)

    return True, ""


def check_upgrade_edition(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if not upgrade.from_edition:
        return True, ""

    from_edition = upgrade.from_edition
    if obj.prototype.bundle.edition not in from_edition:
        msg = 'bundle edition "{}" is not in upgrade list: {}'

        return False, msg.format(obj.prototype.bundle.edition, from_edition)

    return True, ""


def check_upgrade_state(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if obj.locked:
        return False, "object is locked"

    if upgrade.allowed(obj):
        return True, ""
    else:
        return False, "no available states"


def check_upgrade_import(
    obj: Union[Cluster, HostProvider], upgrade: Upgrade
) -> Tuple[bool, str]:  # pylint: disable=too-many-branches
    def get_export(_cbind):
        if _cbind.source_service:
            return _cbind.source_service
        else:
            return _cbind.source_cluster

    def get_import(_cbind):
        if _cbind.service:
            return _cbind.service
        else:
            return _cbind.cluster

    if obj.prototype.type != "cluster":
        return True, ""

    for cbind in ClusterBind.objects.filter(cluster=obj):
        export = get_export(cbind)
        import_obj = get_import(cbind)
        try:
            proto = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=import_obj.prototype.name,
                type=import_obj.prototype.type,
            )
        except Prototype.DoesNotExist:
            msg = "Upgrade does not have new version of {} required for import"
            return False, msg.format(proto_ref(import_obj.prototype))
        try:
            prototype_import = PrototypeImport.objects.get(prototype=proto, name=export.prototype.name)
            if not version_in(export.prototype.version, prototype_import):
                msg = 'Import "{}" of {} versions ({}, {}) does not match export version: {} ({})'
                return (
                    False,
                    msg.format(
                        export.prototype.name,
                        proto_ref(proto),
                        prototype_import.min_version,
                        prototype_import.max_version,
                        export.prototype.version,
                        obj_ref(export),
                    ),
                )
        except PrototypeImport.DoesNotExist:
            cbind.delete()

    for cbind in ClusterBind.objects.filter(source_cluster=obj):
        export = get_export(cbind)
        try:
            proto = Prototype.objects.get(bundle=upgrade.bundle, name=export.prototype.name, type=export.prototype.type)
        except Prototype.DoesNotExist:
            msg = "Upgrade does not have new version of {} required for export"
            return False, msg.format(proto_ref(export.prototype))

        import_obj = get_import(cbind)
        prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export.prototype.name)
        if not version_in(proto.version, prototype_import):
            msg = "Export of {} does not match import versions: ({}, {}) ({})"
            return (
                False,
                msg.format(
                    proto_ref(proto), prototype_import.min_version, prototype_import.max_version, obj_ref(import_obj)
                ),
            )

    return True, ""


def check_upgrade(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if obj.locked:
        concerns = [i.name or "Action lock" for i in obj.concerns.all()]

        return False, f"{obj} has blocking concerns to address: {concerns}"

    check_list = [
        check_upgrade_version,
        check_upgrade_edition,
        check_upgrade_state,
        check_upgrade_import,
    ]
    for func in check_list:
        success, msg = func(obj, upgrade)
        if not success:
            return False, msg

    return True, ""


def switch_hc(obj: Cluster, upgrade: Upgrade) -> None:
    def find_service(service, bundle):
        try:
            return Prototype.objects.get(bundle=bundle, type="service", name=service.prototype.name)
        except Prototype.DoesNotExist:
            return None

    def find_component(component, proto):
        try:
            return Prototype.objects.get(parent=proto, type="component", name=component.prototype.name)
        except Prototype.DoesNotExist:
            return None

    if obj.prototype.type != "cluster":
        return

    for hostcomponent in HostComponent.objects.filter(cluster=obj):
        service_proto = find_service(hostcomponent.service, upgrade.bundle)
        if not service_proto:
            hostcomponent.delete()

            continue

        if not find_component(hostcomponent.component, service_proto):
            hostcomponent.delete()

            continue


def get_upgrade(obj: Union[Cluster, HostProvider], order=None) -> List[Upgrade]:
    def rpm_cmp(obj1, obj2):
        return rpm.compare_versions(obj1.name, obj2.name)

    def rpm_cmp_reverse(obj1, obj2):
        return rpm.compare_versions(obj2.name, obj1.name)

    res = []
    for upg in Upgrade.objects.filter(bundle__name=obj.prototype.bundle.name):
        success, _msg = check_upgrade_version(obj, upg)
        if not success:
            continue

        success, _msg = check_upgrade_edition(obj, upg)
        if not success:
            continue

        success, _msg = check_upgrade_state(obj, upg)
        upg.upgradable = bool(success)
        upgrade_proto = Prototype.objects.filter(bundle=upg.bundle, name=upg.bundle.name).first()
        upg.license = upgrade_proto.license
        if upg.upgradable:
            res.append(upg)

    if order:
        if "name" in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp))
        elif "-name" in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp_reverse))
        else:
            return res
    else:
        return res


def re_apply_following_policies(obj: Cluster | HostProvider) -> None:
    re_apply_object_policy(apply_object=obj)

    if isinstance(obj, Cluster):
        for service in ClusterObject.objects.filter(cluster=obj):
            re_apply_object_policy(apply_object=service)
            for component in ServiceComponent.objects.filter(cluster=obj, service=service):
                re_apply_object_policy(apply_object=component)

    elif isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            re_apply_object_policy(apply_object=host)


def update_components_after_bundle_switch(cluster: Cluster, upgrade: Upgrade) -> None:
    if upgrade.action and upgrade.action.hostcomponentmap:
        logger.info("update component from %s after upgrade with hc_acl", cluster)
        for hc_acl in upgrade.action.hostcomponentmap:
            proto_service = Prototype.objects.filter(
                type="service", bundle=upgrade.bundle, name=hc_acl["service"]
            ).first()
            if not proto_service:
                continue

            try:
                service = ClusterObject.objects.get(cluster=cluster, prototype=proto_service)
                if not ServiceComponent.objects.filter(cluster=cluster, service=service).exists():
                    add_components_to_service(cluster=cluster, service=service)
            except ClusterObject.DoesNotExist:
                add_service_to_cluster(cluster=cluster, proto=proto_service)


def revert_object(obj: ADCMEntity, old_proto: Prototype) -> None:
    if obj.prototype == old_proto:
        return

    obj.prototype = old_proto

    if "config" in obj.before_upgrade:
        config_log = ConfigLog.objects.get(id=obj.before_upgrade["config"])
        obj.config.current = 0
        save_obj_config(obj_conf=obj.config, conf=config_log.config, attr=config_log.attr, desc="revert_upgrade")

    obj.state = obj.before_upgrade["state"]
    obj.before_upgrade = {"state": None}
    obj.save(update_fields=["prototype", "before_upgrade", "state"])


def bundle_revert(obj: Cluster | HostProvider) -> None:  # pylint: disable=too-many-locals
    upgraded_bundle = obj.prototype.bundle
    old_bundle = Bundle.objects.get(pk=obj.before_upgrade["bundle_id"])
    old_proto = Prototype.objects.filter(bundle=old_bundle, name=old_bundle.name).first()
    before_upgrade_hc = obj.before_upgrade.get("hc")
    services = obj.before_upgrade.get("services")

    revert_object(obj=obj, old_proto=old_proto)

    if isinstance(obj, Cluster):
        for service_proto in Prototype.objects.filter(bundle=old_bundle, type="service"):
            service = ClusterObject.objects.filter(cluster=obj, prototype__name=service_proto.name).first()
            if not service:
                continue

            revert_object(obj=service, old_proto=service_proto)
            for component_proto in Prototype.objects.filter(bundle=old_bundle, parent=service_proto, type="component"):
                comp = ServiceComponent.objects.filter(
                    cluster=obj, service=service, prototype__name=component_proto.name
                ).first()

                if comp:
                    revert_object(obj=comp, old_proto=component_proto)
                else:
                    component = ServiceComponent.objects.create(cluster=obj, service=service, prototype=component_proto)
                    obj_conf = init_object_config(proto=component_proto, obj=component)
                    component.config = obj_conf
                    component.save(update_fields=["config"])

        ClusterObject.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        ServiceComponent.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service in services:
            proto = Prototype.objects.get(bundle=old_bundle, name=service, type="service")
            try:
                ClusterObject.objects.get(prototype=proto)
            except ClusterObject.DoesNotExist:
                add_service_to_cluster(cluster=obj, proto=proto)

        host_comp_list = []
        for hostcomponent in before_upgrade_hc:
            host = Host.objects.get(fqdn=hostcomponent["host"], cluster=obj)
            service = ClusterObject.objects.get(prototype__name=hostcomponent["service"], cluster=obj)
            comp = ServiceComponent.objects.get(
                prototype__name=hostcomponent["component"], cluster=obj, service=service
            )
            host_comp_list.append((service, host, comp))

        save_hc(cluster=obj, host_comp_list=host_comp_list)

    if isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type="host", name=host.prototype.name)
            revert_object(obj=host, old_proto=old_host_proto)


def set_before_upgrade(obj: ADCMEntity) -> None:
    obj.before_upgrade["state"] = obj.state
    if obj.config:
        obj.before_upgrade["config"] = obj.config.current

    if isinstance(obj, Cluster):
        hc_map = []
        for hostcomponent in HostComponent.objects.filter(cluster=obj):
            hc_map.append(
                {
                    "service": hostcomponent.service.name,
                    "component": hostcomponent.component.name,
                    "host": hostcomponent.host.name,
                }
            )

        obj.before_upgrade["hc"] = hc_map
        obj.before_upgrade["services"] = [
            service.prototype.name for service in ClusterObject.objects.filter(cluster=obj)
        ]

    obj.save(update_fields=["before_upgrade"])


def update_before_upgrade(obj: Cluster | HostProvider) -> None:
    set_before_upgrade(obj=obj)

    if isinstance(obj, Cluster):
        for service in ClusterObject.objects.filter(cluster=obj):
            set_before_upgrade(obj=service)
            for component in ServiceComponent.objects.filter(service=service, cluster=obj):
                set_before_upgrade(obj=component)

    if isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            set_before_upgrade(obj=host)


def do_upgrade(
    obj: Cluster | HostProvider,
    upgrade: Upgrade,
    config: dict,
    attr: dict,
    hostcomponent: list,
) -> dict:
    old_proto = obj.prototype
    check_license(proto=obj.prototype)
    upgrade_proto = Prototype.objects.filter(bundle=upgrade.bundle, name=upgrade.bundle.name).first()
    check_license(proto=upgrade_proto)
    success, msg = check_upgrade(obj=obj, upgrade=upgrade)
    if not success:
        return raise_adcm_ex("UPGRADE_ERROR", msg)
    logger.info("upgrade %s version %s (upgrade #%s)", obj_ref(obj), old_proto.version, upgrade.id)

    task_id = None

    obj.before_upgrade["bundle_id"] = old_proto.bundle.id
    update_before_upgrade(obj=obj)

    if not upgrade.action:
        bundle_switch(obj=obj, upgrade=upgrade)
        if upgrade.state_on_success:
            obj.state = upgrade.state_on_success
            obj.save()
    else:
        task = start_task(
            action=upgrade.action, obj=obj, conf=config, attr=attr, hostcomponent=hostcomponent, hosts=[], verbose=False
        )
        task_id = task.id

    obj.refresh_from_db()
    re_apply_following_policies(obj=obj)

    return {"id": obj.id, "upgradable": bool(get_upgrade(obj)), "task_id": task_id}


def bundle_switch(obj: Cluster | HostProvider, upgrade: Upgrade) -> None:
    new_proto = None
    old_proto = obj.prototype
    if old_proto.type == "cluster":
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type="cluster")
    elif old_proto.type == "provider":
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type="provider")
    else:
        raise_adcm_ex("UPGRADE_ERROR", "can upgrade only cluster or host provider")

    with transaction.atomic():
        obj.prototype = new_proto
        obj.save()
        switch_config(obj, new_proto, old_proto)

        if obj.prototype.type == "cluster":
            switch_services(upgrade, obj)
            if old_proto.allow_maintenance_mode != new_proto.allow_maintenance_mode:
                Host.objects.filter(cluster=obj).update(maintenance_mode=MaintenanceMode.OFF)
        elif obj.prototype.type == "provider":
            switch_hosts(upgrade, obj)

        update_hierarchy_issues(obj)
        if isinstance(obj, Cluster):
            update_components_after_bundle_switch(obj, upgrade)

    logger.info("upgrade %s OK to version %s", obj_ref(obj), obj.prototype.version)
    post_event(event="upgrade", obj=obj, details={"type": "version", "value": str(obj.prototype.version)})
