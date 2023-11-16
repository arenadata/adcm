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

from cm.adcm_config.config import (
    init_object_config,
    make_object_config,
    save_obj_config,
    switch_config,
)
from cm.adcm_config.utils import proto_ref
from cm.api import (
    add_components_to_service,
    add_service_to_cluster,
    check_license,
    is_version_suitable,
    save_hc,
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
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
    Upgrade,
)
from cm.status_api import send_prototype_and_state_update_event
from cm.utils import obj_ref
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rbac.models import Policy
from version_utils import rpm


def switch_object(obj: Host | ClusterObject, new_prototype: Prototype) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))

    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])

    switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype)


def switch_services(upgrade: Upgrade, cluster: Cluster) -> None:
    for service in ClusterObject.objects.filter(cluster=cluster):
        check_license(prototype=service.prototype)
        try:
            new_prototype = Prototype.objects.get(bundle=upgrade.bundle, type="service", name=service.prototype.name)
            check_license(prototype=new_prototype)
            switch_object(obj=service, new_prototype=new_prototype)
            switch_components(cluster=cluster, service=service, new_component_prototype=new_prototype)
        except Prototype.DoesNotExist:
            service.delete()

    switch_hc(obj=cluster, upgrade=upgrade)


def switch_components(cluster: Cluster, service: ClusterObject, new_component_prototype: Prototype) -> None:
    for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(
                parent=new_component_prototype, type="component", name=component.prototype.name
            )
            switch_object(obj=component, new_prototype=new_comp_prototype)
        except Prototype.DoesNotExist:
            component.delete()

    for component_prototype in Prototype.objects.filter(parent=new_component_prototype, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": component_prototype}
        if not ServiceComponent.objects.filter(**kwargs).exists():
            component = ServiceComponent.objects.create(**kwargs)
            make_object_config(obj=component, prototype=component_prototype)


def switch_hosts(upgrade: Upgrade, provider: HostProvider) -> None:
    for prototype in Prototype.objects.filter(bundle=upgrade.bundle, type="host"):
        for host in Host.objects.filter(provider=provider, prototype__name=prototype.name):
            switch_object(host, prototype)


def check_upgrade_version(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.min_strict:
        if rpm.compare_versions(prototype.version, upgrade.min_version) <= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is less than or equal to upgrade min version {upgrade.min_version}",
            )
    else:
        if rpm.compare_versions(prototype.version, upgrade.min_version) < 0:
            return (
                False,
                "{prototype.type} version {prototype.version} is less than upgrade min version {upgrade.min_version}",
            )

    if upgrade.max_strict:
        if rpm.compare_versions(prototype.version, upgrade.max_version) >= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is more than or equal to upgrade max version {upgrade.max_version}",
            )
    else:
        if rpm.compare_versions(prototype.version, upgrade.max_version) > 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} is more than upgrade max version {upgrade.max_version}",
            )

    return True, ""


def check_upgrade_edition(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.from_edition == "any":
        return True, ""

    if upgrade.from_edition and prototype.bundle.edition not in upgrade.from_edition:
        return False, f'bundle edition "{prototype.bundle.edition}" is not in upgrade list: {upgrade.from_edition}'

    return True, ""


def check_upgrade_state(obj: Cluster | HostProvider, upgrade: Upgrade) -> tuple[bool, str]:
    if obj.locked:
        return False, "object is locked"

    if upgrade.allowed(obj):
        return True, ""
    else:
        return False, "no available states"


def check_upgrade_import(
    obj: Cluster,
    upgrade: Upgrade,
) -> tuple[bool, str]:
    for cbind in ClusterBind.objects.filter(cluster=obj):
        export = cbind.source_service if cbind.source_service else cbind.source_cluster
        import_obj = cbind.service if cbind.service else cbind.cluster
        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=import_obj.prototype.name,
                type=import_obj.prototype.type,
            )
        except Prototype.DoesNotExist:
            return (
                False,
                f"Upgrade does not have new version of "
                f'{import_obj.prototype.type} "{import_obj.prototype.name}" {import_obj.prototype.version}',
            )

        try:
            prototype_import = PrototypeImport.objects.get(prototype=prototype, name=export.prototype.name)
            if not is_version_suitable(export.prototype.version, prototype_import):
                return (
                    False,
                    f'Import "{export.prototype.name}" of {prototype.type} "{prototype.name}" {prototype.version} '
                    f"versions ({prototype_import.min_version}, {prototype_import.max_version}) "
                    f"does not match export version: {export.prototype.version} ({obj_ref(obj=export)})",
                )
        except PrototypeImport.DoesNotExist:
            cbind.delete()

    for cbind in ClusterBind.objects.filter(source_cluster=obj):
        export = cbind.source_service if cbind.source_service else cbind.source_cluster
        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=export.prototype.name,
                type=export.prototype.type,
            )
        except Prototype.DoesNotExist:
            return (
                False,
                f"Upgrade does not have new version of "
                f'{export.prototype.type} "{export.prototype.name}" {export.prototype.version} required for export',
            )

        import_obj = cbind.service if cbind.service else cbind.cluster
        prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export.prototype.name)
        if not is_version_suitable(prototype.version, prototype_import):
            return (
                False,
                f'Export of {prototype.type} "{prototype.name}" {prototype.version} '
                f"does not match import versions: ({prototype_import.min_version}, "
                f"{prototype_import.max_version}) ({obj_ref(obj=import_obj)})",
            )

    return True, ""


def check_upgrade(obj: Cluster | HostProvider, upgrade: Upgrade) -> tuple[bool, str]:
    if obj.locked:
        concerns = [concern.name or "Action lock" for concern in obj.concerns.order_by("id")]

        return False, f"{obj} has blocking concerns to address: {concerns}"

    success, msg = check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    success, msg = check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    if not upgrade.allowed(obj=obj):
        return False, "no available states"

    if obj.prototype.type == ObjectType.CLUSTER:
        success, msg = check_upgrade_import(obj=obj, upgrade=upgrade)
        if not success:
            return False, msg

    return True, ""


def switch_hc(obj: Cluster, upgrade: Upgrade) -> None:
    for hostcomponent in HostComponent.objects.filter(cluster=obj):
        service_prototype = Prototype.objects.filter(
            bundle=upgrade.bundle,
            type="service",
            name=hostcomponent.service.prototype.name,
        ).first()
        if not service_prototype:
            hostcomponent.delete()

            continue

        if not Prototype.objects.filter(
            parent=service_prototype,
            type="component",
            name=hostcomponent.component.prototype.name,
        ).first():
            hostcomponent.delete()

            continue


def get_upgrade(obj: Cluster | HostProvider, order=None) -> list[Upgrade]:
    res = []
    for upgrade in Upgrade.objects.filter(bundle__name=obj.prototype.bundle.name):
        success, _ = check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
        if not success:
            continue

        success, _ = check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
        if not success:
            continue

        if obj.locked or not upgrade.allowed(obj=obj):
            continue

        upgrade_proto = Prototype.objects.filter(bundle=upgrade.bundle, name=upgrade.bundle.name).first()
        upgrade.license = upgrade_proto.license
        res.append(upgrade)

    if order:
        if "name" in order:
            return sorted(
                res,
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: rpm.compare_versions(obj1.name, obj2.name)),
            )

        if "-name" in order:
            return sorted(
                res,
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: rpm.compare_versions(obj2.name, obj2.name)),
            )

    return res


def re_apply_policy_for_upgrade(obj: Cluster | HostProvider) -> None:
    obj_type_map = {obj: ContentType.objects.get_for_model(obj)}

    if isinstance(obj, Cluster):
        for service in ClusterObject.objects.filter(cluster=obj):
            obj_type_map[service] = ContentType.objects.get_for_model(service)
            for component in ServiceComponent.objects.filter(cluster=obj, service=service):
                obj_type_map[component] = ContentType.objects.get_for_model(component)
    elif isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            obj_type_map[host] = ContentType.objects.get_for_model(host)

    for policy_object, content_type in obj_type_map.items():
        for policy in Policy.objects.filter(object__object_id=policy_object.id, object__content_type=content_type):
            policy.apply()


def update_components_after_bundle_switch(cluster: Cluster, upgrade: Upgrade) -> None:
    if upgrade.action and upgrade.action.hostcomponentmap:
        logger.info("update component from %s after upgrade with hc_acl", cluster)
        for hc_acl in upgrade.action.hostcomponentmap:
            proto_service = Prototype.objects.filter(
                type="service",
                bundle=upgrade.bundle,
                name=hc_acl["service"],
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

    if "config_id" in obj.before_upgrade:
        config_log = ConfigLog.objects.get(id=obj.before_upgrade["config_id"])
        obj.config.current = 0
        save_obj_config(obj_conf=obj.config, conf=config_log.config, attr=config_log.attr, desc="revert_upgrade")
    else:
        obj.config = None

    obj.state = obj.before_upgrade["state"]
    obj.before_upgrade = {"state": None}
    obj.save(update_fields=["prototype", "config", "state", "before_upgrade"])


def bundle_revert(obj: Cluster | HostProvider) -> None:  # pylint: disable=too-many-locals
    upgraded_bundle = obj.prototype.bundle
    old_bundle = Bundle.objects.get(pk=obj.before_upgrade["bundle_id"])
    old_proto = Prototype.objects.filter(bundle=old_bundle, name=old_bundle.name).first()
    before_upgrade_hc = obj.before_upgrade.get("hc")
    service_names = obj.before_upgrade.get("services")

    revert_object(obj=obj, old_proto=old_proto)

    if isinstance(obj, Cluster):
        for service_prototype in Prototype.objects.filter(bundle=old_bundle, type="service"):
            service = ClusterObject.objects.filter(cluster=obj, prototype__name=service_prototype.name).first()
            if not service:
                continue

            revert_object(obj=service, old_proto=service_prototype)
            for component_prototype in Prototype.objects.filter(
                bundle=old_bundle, parent=service_prototype, type="component"
            ):
                component = ServiceComponent.objects.filter(
                    cluster=obj,
                    service=service,
                    prototype__name=component_prototype.name,
                ).first()

                if component:
                    revert_object(obj=component, old_proto=component_prototype)
                else:
                    component = ServiceComponent.objects.create(
                        cluster=obj,
                        service=service,
                        prototype=component_prototype,
                    )
                    obj_conf = init_object_config(proto=component_prototype, obj=component)
                    component.config = obj_conf
                    component.save(update_fields=["config"])

        ClusterObject.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        ServiceComponent.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service_name in service_names:
            prototype = Prototype.objects.get(bundle=old_bundle, name=service_name, type="service")

            if not ClusterObject.objects.filter(prototype=prototype, cluster=obj).exists():
                add_service_to_cluster(cluster=obj, proto=prototype)

        host_comp_list = []
        for hostcomponent in before_upgrade_hc:
            host = Host.objects.get(fqdn=hostcomponent["host"], cluster=obj)
            service = ClusterObject.objects.get(prototype__name=hostcomponent["service"], cluster=obj)
            component = ServiceComponent.objects.get(
                prototype__name=hostcomponent["component"],
                cluster=obj,
                service=service,
            )
            host_comp_list.append((service, host, component))

        save_hc(cluster=obj, host_comp_list=host_comp_list)

    if isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type="host", name=host.prototype.name)
            revert_object(obj=host, old_proto=old_host_proto)


def set_before_upgrade(obj: ADCMEntity) -> None:
    obj.before_upgrade["state"] = obj.state
    if obj.config:
        obj.before_upgrade["config_id"] = obj.config.current

    if groups := GroupConfig.objects.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)):
        obj.before_upgrade["groups"] = {}

        for group in groups:
            obj.before_upgrade["groups"][group.name] = {"group_config_id": group.config.current}

    if isinstance(obj, Cluster):
        hc_map = []
        for hostcomponent in HostComponent.objects.filter(cluster=obj):
            hc_map.append(
                {
                    "service": hostcomponent.service.name,
                    "component": hostcomponent.component.name,
                    "host": hostcomponent.host.name,
                },
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
    check_license(prototype=obj.prototype)
    upgrade_prototype = Prototype.objects.filter(
        bundle=upgrade.bundle, name=upgrade.bundle.name, type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER]
    ).first()
    check_license(prototype=upgrade_prototype)

    success, msg = check_upgrade(obj=obj, upgrade=upgrade)
    if not success:
        return raise_adcm_ex("UPGRADE_ERROR", msg)

    logger.info("upgrade %s version %s (upgrade #%s)", obj_ref(obj), obj.prototype.version, upgrade.id)

    task_id = None

    obj.before_upgrade["bundle_id"] = obj.prototype.bundle.pk
    update_before_upgrade(obj=obj)

    if not upgrade.action:
        bundle_switch(obj=obj, upgrade=upgrade)

        if upgrade.state_on_success:
            obj.state = upgrade.state_on_success
            obj.save(update_fields=["state"])

        send_prototype_and_state_update_event(object_=obj)
    else:
        task = start_task(
            action=upgrade.action,
            obj=obj,
            conf=config,
            attr=attr,
            hostcomponent=hostcomponent,
            hosts=[],
            verbose=False,
        )
        task_id = task.id

    obj.refresh_from_db()

    return {"id": obj.id, "upgradable": bool(get_upgrade(obj=obj)), "task_id": task_id}


def bundle_switch(obj: Cluster | HostProvider, upgrade: Upgrade) -> None:
    new_prototype = None
    old_prototype = obj.prototype
    if old_prototype.type == "cluster":
        new_prototype = Prototype.objects.get(bundle=upgrade.bundle, type="cluster")
    elif old_prototype.type == "provider":
        new_prototype = Prototype.objects.get(bundle=upgrade.bundle, type="provider")
    else:
        raise_adcm_ex("UPGRADE_ERROR", "can upgrade only cluster or host provider")

    with transaction.atomic():
        obj.prototype = new_prototype
        obj.save(update_fields=["prototype"])
        switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype)

        if obj.prototype.type == "cluster":
            switch_services(upgrade=upgrade, cluster=obj)
            if old_prototype.allow_maintenance_mode != new_prototype.allow_maintenance_mode:
                Host.objects.filter(cluster=obj).update(maintenance_mode=MaintenanceMode.OFF)
        elif obj.prototype.type == "provider":
            switch_hosts(upgrade=upgrade, provider=obj)

        update_hierarchy_issues(obj=obj)
        if isinstance(obj, Cluster):
            update_components_after_bundle_switch(cluster=obj, upgrade=upgrade)

    obj.refresh_from_db()
    re_apply_policy_for_upgrade(obj=obj)
    logger.info("upgrade %s OK to version %s", obj_ref(obj=obj), obj.prototype.version)
