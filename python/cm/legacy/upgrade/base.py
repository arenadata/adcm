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

from typing import cast
import functools

from adcm_version import compare_prototype_versions
from core.types import Descriptor

from cm.converters import orm_object_to_core_type
from cm.legacy.api import is_version_suitable
from cm.legacy.upgrade.before_upgrade_schemas import (
    ActionHostGroupBeforeUpgrade,
    BeforeUpgrade,
    ClusterBeforeUpgrade,
    ComponentBeforeUpgrade,
    ConfigHostGroupWithIdConfigBeforeUpgrade,
    HostBeforeUpgrade,
    ProviderBeforeUpgrade,
    ServiceBeforeUpgrade,
    ServiceHostComponentMapBeforeUpgrade,
)
from cm.legacy.utils import obj_ref
from cm.models import (
    Cluster,
    ClusterBind,
    Component,
    Host,
    MainObject,
    ObjectType,
    Prototype,
    PrototypeImport,
    Provider,
    Service,
    Upgrade,
)
from cm.transition.action import RetrieveStartImpossibleReason


class DifferentBundleError(Exception):
    ...


def check_upgrade(
    obj: Cluster | Provider, upgrade: Upgrade, retrieve_sir: RetrieveStartImpossibleReason | None
) -> tuple[bool, str]:
    _check_same_bundle(obj=obj, upgrade=upgrade)

    if retrieve_sir and (
        start_impossible_reason := retrieve_sir.for_upgrade_target(
            target=Descriptor(id=obj.id, type=orm_object_to_core_type(obj))
        )
    ):
        return False, start_impossible_reason

    if obj.locked:
        concerns = [concern.name or "Action lock" for concern in obj.concerns.order_by("id")]

        return False, f"{obj} has blocking concerns to address: {concerns}"

    success, msg = _check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    success, msg = _check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    if not upgrade.allowed(obj=obj):
        return False, "no available states"

    if obj.prototype.type == ObjectType.CLUSTER:
        success, msg = _check_upgrade_import(obj=cast(Cluster, obj), upgrade=upgrade)
        if not success:
            return False, msg

    return True, ""


def get_upgrade(obj: Cluster | Provider, order=None) -> list[Upgrade]:
    res = []
    for upgrade in Upgrade.objects.filter(bundle__name=obj.prototype.bundle.name):
        success, _ = _check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
        if not success:
            continue

        success, _ = _check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
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
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: compare_prototype_versions(obj1.name, obj2.name)),
            )

        if "-name" in order:
            return sorted(
                res,
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: compare_prototype_versions(obj2.name, obj2.name)),
            )

    return res


def update_before_upgrade(obj: Cluster | Provider) -> None:
    if isinstance(obj, Cluster):
        _set_before_upgrade(obj=obj, before_upgrade=ClusterBeforeUpgrade(**obj.before_upgrade))

        for service in Service.objects.filter(cluster=obj):
            _set_before_upgrade(obj=service, before_upgrade=ServiceBeforeUpgrade())

            for component in Component.objects.filter(service=service, cluster=obj):
                _set_before_upgrade(obj=component, before_upgrade=ComponentBeforeUpgrade())

    if isinstance(obj, Provider):
        _set_before_upgrade(obj=obj, before_upgrade=ProviderBeforeUpgrade(**obj.before_upgrade))

        for host in Host.objects.filter(provider=obj):
            _set_before_upgrade(obj=host, before_upgrade=HostBeforeUpgrade())


def _set_before_upgrade(obj: MainObject, before_upgrade: BeforeUpgrade) -> None:
    before_upgrade.state = obj.state

    if obj.config:
        before_upgrade.config_id = obj.config.current

    if not isinstance(obj, Host):
        before_upgrade.config_host_groups = {
            group.name: ConfigHostGroupWithIdConfigBeforeUpgrade(
                config_id=group.config.current,
                hosts=list(group.hosts.values_list("fqdn", flat=True)),
            )
            for group in obj.config_host_group.all()
        }

    if not isinstance(obj, Provider | Host):
        before_upgrade.action_host_groups = {
            group.name: ActionHostGroupBeforeUpgrade(hosts=list(group.hosts.values_list("fqdn", flat=True)))
            for group in obj.action_host_group.all()
        }

    if isinstance(obj, Cluster):
        before_upgrade.hc = [
            ServiceHostComponentMapBeforeUpgrade(
                service=service,
                component=component,
                host=host,
            )
            for service, component, host in obj.hostcomponent_set.values_list(
                "service__prototype__name", "component__prototype__name", "host__fqdn"
            )
        ]
        before_upgrade.services = list(
            obj.services.select_related("prototype").values_list("prototype__name", flat=True)
        )

    obj.before_upgrade = before_upgrade.model_dump()
    obj.save(update_fields=["before_upgrade"])


def _check_same_bundle(obj: Cluster | Provider, upgrade: Upgrade) -> None:
    # preserving old behavior: 404 on foreign upgrade error. See ADCM-7976
    if upgrade.bundle.name != obj.prototype.bundle.name:
        raise DifferentBundleError()


def _check_upgrade_version(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.min_strict:
        if compare_prototype_versions(prototype.version, upgrade.min_version) <= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is less than or equal to upgrade min version {upgrade.min_version}",
            )
    else:
        if compare_prototype_versions(prototype.version, upgrade.min_version) < 0:
            return (
                False,
                "{prototype.type} version {prototype.version} is less than upgrade min version {upgrade.min_version}",
            )

    if upgrade.max_strict:
        if compare_prototype_versions(prototype.version, upgrade.max_version) >= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is more than or equal to upgrade max version {upgrade.max_version}",
            )
    else:
        if compare_prototype_versions(prototype.version, upgrade.max_version) > 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} is more than upgrade max version {upgrade.max_version}",
            )

    return True, ""


def _check_upgrade_edition(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.from_edition == "any":
        return True, ""

    if upgrade.from_edition and prototype.bundle.edition not in upgrade.from_edition:
        return False, f'bundle edition "{prototype.bundle.edition}" is not in upgrade list: {upgrade.from_edition}'

    return True, ""


def _check_upgrade_import(obj: Cluster, upgrade: Upgrade) -> tuple[bool, str]:
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
            pass

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
