# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain a
# copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
from typing import Union, Tuple, List

from django.db import transaction
from version_utils import rpm

import cm.issue
import cm.job
import cm.status_api
from cm.adcm_config import proto_ref, obj_ref, switch_config, make_object_config
from cm.api import check_license, version_in, add_components_to_service, add_service_to_cluster
from cm.errors import raise_AdcmEx as err
from cm.logger import log
from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    Prototype,
    PrototypeImport,
    ServiceComponent,
    Upgrade,
    MaintenanceModeType,
)


def switch_object(obj: Union[Host, ClusterObject], new_prototype: Prototype) -> None:
    """Upgrade object"""
    log.info('upgrade switch from %s to %s', proto_ref(obj.prototype), proto_ref(new_prototype))
    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save()
    switch_config(obj, new_prototype, old_prototype)


def switch_services(upgrade: Upgrade, cluster: Cluster) -> None:
    """Upgrade services and component"""

    for service in ClusterObject.objects.filter(cluster=cluster):
        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle, type='service', name=service.prototype.name
            )
            switch_object(service, prototype)
            switch_components(cluster, service, prototype)
        except Prototype.DoesNotExist:
            service.delete()

    switch_hc(cluster, upgrade)


def switch_components(cluster: Cluster, co: ClusterObject, new_co_proto: Prototype) -> None:
    """Upgrade components"""
    for sc in ServiceComponent.objects.filter(cluster=cluster, service=co):
        try:
            new_sc_prototype = Prototype.objects.get(
                parent=new_co_proto, type='component', name=sc.prototype.name
            )
            switch_object(sc, new_sc_prototype)
        except Prototype.DoesNotExist:
            sc.delete()

    for sc_proto in Prototype.objects.filter(parent=new_co_proto, type='component'):
        kwargs = dict(cluster=cluster, service=co, prototype=sc_proto)
        if not ServiceComponent.objects.filter(**kwargs).exists():
            sc = ServiceComponent.objects.create(**kwargs)
            make_object_config(sc, sc_proto)


def switch_hosts(upgrade: Upgrade, provider: HostProvider) -> None:
    """Upgrade hosts"""
    for prototype in Prototype.objects.filter(bundle=upgrade.bundle, type='host'):
        for host in Host.objects.filter(provider=provider, prototype__name=prototype.name):
            switch_object(host, prototype)


def check_upgrade_version(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    proto = obj.prototype
    # log.debug('check %s < %s > %s', upgrade.min_version, proto.version, upgrade.max_version)
    if upgrade.min_strict:
        if rpm.compare_versions(proto.version, upgrade.min_version) <= 0:
            msg = '{} version {} is less than or equal to upgrade min version {}'
            return False, msg.format(proto.type, proto.version, upgrade.min_version)
    else:
        if rpm.compare_versions(proto.version, upgrade.min_version) < 0:
            msg = '{} version {} is less than upgrade min version {}'
            return False, msg.format(proto.type, proto.version, upgrade.min_version)
    if upgrade.max_strict:
        if rpm.compare_versions(proto.version, upgrade.max_version) >= 0:
            msg = '{} version {} is more than or equal to upgrade max version {}'
            return False, msg.format(proto.type, proto.version, upgrade.max_version)
    else:
        if rpm.compare_versions(proto.version, upgrade.max_version) > 0:
            msg = '{} version {} is more than upgrade max version {}'
            return False, msg.format(proto.type, proto.version, upgrade.max_version)
    return True, ''


def check_upgrade_edition(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if not upgrade.from_edition:
        return True, ''
    from_edition = upgrade.from_edition
    if obj.prototype.bundle.edition not in from_edition:
        msg = 'bundle edition "{}" is not in upgrade list: {}'
        return False, msg.format(obj.prototype.bundle.edition, from_edition)
    return True, ''


def check_upgrade_state(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if obj.locked:
        return False, 'object is locked'
    if upgrade.allowed(obj):
        return True, ''
    else:
        return False, 'no available states'


def check_upgrade_import(
    obj: Union[Cluster, HostProvider], upgrade: Upgrade
) -> Tuple[bool, str]:  # pylint: disable=too-many-branches
    def get_export(cbind):
        if cbind.source_service:
            return cbind.source_service
        else:
            return cbind.source_cluster

    def get_import(cbind):  # pylint: disable=redefined-outer-name
        if cbind.service:
            return cbind.service
        else:
            return cbind.cluster

    if obj.prototype.type != 'cluster':
        return True, ''

    for cbind in ClusterBind.objects.filter(cluster=obj):
        export = get_export(cbind)
        impr_obj = get_import(cbind)
        try:
            proto = Prototype.objects.get(
                bundle=upgrade.bundle, name=impr_obj.prototype.name, type=impr_obj.prototype.type
            )
        except Prototype.DoesNotExist:
            msg = 'Upgrade does not have new version of {} required for import'
            return False, msg.format(proto_ref(impr_obj.prototype))
        try:
            pi = PrototypeImport.objects.get(prototype=proto, name=export.prototype.name)
            if not version_in(export.prototype.version, pi):
                msg = 'Import "{}" of {} versions ({}, {}) does not match export version: {} ({})'
                return (
                    False,
                    msg.format(
                        export.prototype.name,
                        proto_ref(proto),
                        pi.min_version,
                        pi.max_version,
                        export.prototype.version,
                        obj_ref(export),
                    ),
                )
        except PrototypeImport.DoesNotExist:
            # msg = 'New version of {} does not have import "{}"'   # ADCM-1507
            # return False, msg.format(proto_ref(proto), export.prototype.name)
            cbind.delete()

    for cbind in ClusterBind.objects.filter(source_cluster=obj):
        export = get_export(cbind)
        try:
            proto = Prototype.objects.get(
                bundle=upgrade.bundle, name=export.prototype.name, type=export.prototype.type
            )
        except Prototype.DoesNotExist:
            msg = 'Upgrade does not have new version of {} required for export'
            return False, msg.format(proto_ref(export.prototype))
        import_obj = get_import(cbind)
        pi = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export.prototype.name)
        if not version_in(proto.version, pi):
            msg = 'Export of {} does not match import versions: ({}, {}) ({})'
            return (
                False,
                msg.format(proto_ref(proto), pi.min_version, pi.max_version, obj_ref(import_obj)),
            )

    return True, ''


def check_upgrade(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> Tuple[bool, str]:
    if obj.locked:
        concerns = [i.name or 'Action lock' for i in obj.concerns.all()]
        return False, f'{obj} has blocking concerns to address: {concerns}'

    check_list = [
        check_upgrade_version,
        check_upgrade_edition,
        check_upgrade_state,
        check_upgrade_import,
    ]
    for func in check_list:
        ok, msg = func(obj, upgrade)
        if not ok:
            return False, msg
    return True, ''


def switch_hc(obj: Cluster, upgrade: Upgrade) -> None:
    def find_service(service, bundle):
        try:
            return Prototype.objects.get(bundle=bundle, type='service', name=service.prototype.name)
        except Prototype.DoesNotExist:
            return None

    def find_component(component, proto):
        try:
            return Prototype.objects.get(
                parent=proto, type='component', name=component.prototype.name
            )
        except Prototype.DoesNotExist:
            return None

    if obj.prototype.type != 'cluster':
        return

    for hc in HostComponent.objects.filter(cluster=obj):
        service_proto = find_service(hc.service, upgrade.bundle)
        if not service_proto:
            hc.delete()
            continue
        if not find_component(hc.component, service_proto):
            hc.delete()
            continue


def get_upgrade(obj: Union[Cluster, HostProvider], order=None) -> List[Upgrade]:
    def rpm_cmp(obj1, obj2):
        return rpm.compare_versions(obj1.name, obj2.name)

    def rpm_cmp_reverse(obj1, obj2):
        return rpm.compare_versions(obj2.name, obj1.name)

    res = []
    for upg in Upgrade.objects.filter(bundle__name=obj.prototype.bundle.name):
        ok, _msg = check_upgrade_version(obj, upg)
        if not ok:
            continue
        ok, _msg = check_upgrade_edition(obj, upg)
        if not ok:
            continue
        ok, _msg = check_upgrade_state(obj, upg)
        upg.upgradable = bool(ok)
        upg.license = upg.bundle.license
        if upg.upgradable:
            res.append(upg)

    #  cm.issue.update_hierarchy_issues(obj)
    if order:
        if 'name' in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp))
        elif '-name' in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp_reverse))
        else:
            return res
    else:
        return res


def update_components_after_bundle_switch(cluster, upgrade):
    if upgrade.action and upgrade.action.hostcomponentmap:
        log.info('update component from %s after upgrade with hc_acl', cluster)
        for hc_acl in upgrade.action.hostcomponentmap:
            proto_service = Prototype.objects.filter(
                type='service', bundle=upgrade.bundle, name=hc_acl['service']
            ).first()
            if not proto_service:
                continue
            try:
                service = ClusterObject.objects.get(cluster=cluster, prototype=proto_service)
                if not ServiceComponent.objects.filter(cluster=cluster, service=service).exists():
                    add_components_to_service(cluster, service)
            except ClusterObject.DoesNotExist:
                add_service_to_cluster(cluster, proto_service)


def do_upgrade(
    obj: Union[Cluster, HostProvider],
    upgrade: Upgrade,
    config: dict,
    attr: dict,
    hc: list,
) -> dict:
    old_proto = obj.prototype
    check_license(obj.prototype.bundle)
    check_license(upgrade.bundle)
    ok, msg = check_upgrade(obj, upgrade)
    if not ok:
        return err('UPGRADE_ERROR', msg)
    log.info('upgrade %s version %s (upgrade #%s)', obj_ref(obj), old_proto.version, upgrade.id)

    task_id = None
    if not upgrade.action:
        bundle_switch(obj, upgrade)
        if upgrade.state_on_success:
            obj.before_upgrade['state'] = obj.state
            obj.state = upgrade.state_on_success
            obj.save()
    else:
        task = cm.job.start_task(upgrade.action, obj, config, attr, hc, [], False)
        task_id = task.id

    obj.refresh_from_db()

    return {'id': obj.id, 'upgradable': bool(get_upgrade(obj)), 'task_id': task_id}


def bundle_switch(obj: Union[Cluster, HostProvider], upgrade: Upgrade):
    old_proto = obj.prototype
    if old_proto.type == 'cluster':
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type='cluster')
    elif old_proto.type == 'provider':
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type='provider')
    else:
        err('UPGRADE_ERROR', 'can upgrade only cluster or host provider')

    with transaction.atomic():
        obj.prototype = new_proto
        obj.save()
        switch_config(obj, new_proto, old_proto)

        if obj.prototype.type == 'cluster':
            switch_services(upgrade, obj)
            if not old_proto.allow_maintenance_mode and new_proto.allow_maintenance_mode:
                Host.objects.filter(cluster=obj).update(maintenance_mode=MaintenanceModeType.Off)
            elif old_proto.allow_maintenance_mode and not new_proto.allow_maintenance_mode:
                Host.objects.filter(cluster=obj).update(
                    maintenance_mode=MaintenanceModeType.Disabled
                )
        elif obj.prototype.type == 'provider':
            switch_hosts(upgrade, obj)
        cm.issue.update_hierarchy_issues(obj)
        if isinstance(obj, Cluster):
            update_components_after_bundle_switch(obj, upgrade)
    log.info('upgrade %s OK to version %s', obj_ref(obj), obj.prototype.version)
    cm.status_api.post_event(
        'upgrade', obj.prototype.type, obj.id, 'version', str(obj.prototype.version)
    )
