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
import cm.status_api
from cm.adcm_config import proto_ref, obj_ref, switch_config, make_object_config
from cm.errors import raise_AdcmEx as err
from cm.logger import log
from cm.models import (
    Bundle,
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
)


def check_license(bundle: Bundle) -> None:
    if bundle.license == 'unaccepted':
        msg = 'License for bundle "{}" {} {} is not accepted'
        err('LICENSE_ERROR', msg.format(bundle.name, bundle.version, bundle.edition))


def version_in(version: str, ver: PrototypeImport) -> bool:
    # log.debug('version_in: %s < %s > %s', ver.min_version, version, ver.max_version)
    if ver.min_strict:
        if rpm.compare_versions(version, ver.min_version) <= 0:
            return False
    elif ver.min_version:
        if rpm.compare_versions(version, ver.min_version) < 0:
            return False
    if ver.max_strict:
        if rpm.compare_versions(version, ver.max_version) >= 0:
            return False
    elif ver.max_version:
        if rpm.compare_versions(version, ver.max_version) > 0:
            return False
    return True


def switch_object(obj: Union[Host, ClusterObject], new_prototype: Prototype) -> None:
    """Upgrade object"""
    log.info('upgrade switch from %s to %s', proto_ref(obj.prototype), proto_ref(new_prototype))
    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save()
    switch_config(obj, new_prototype, old_prototype)


def switch_services(upgrade: Upgrade, cluster: Cluster) -> None:
    """Upgrade services and component"""

    for prototype in Prototype.objects.filter(bundle=upgrade.bundle, type='service'):
        try:
            co = ClusterObject.objects.get(cluster=cluster, prototype__name=prototype.name)
            switch_object(co, prototype)
            switch_components(cluster, co, prototype)
        except ClusterObject.DoesNotExist:
            # co.delete() ?!
            pass
    switch_hc(cluster, upgrade)


def switch_components(cluster: Cluster, co: ClusterObject, new_co_proto: Prototype) -> None:
    """Upgrade components"""
    for sc in ServiceComponent.objects.filter(cluster=cluster, service=co):
        try:
            new_sc_prototype = Prototype.objects.get(
                parent=new_co_proto, type='component', name=sc.prototype.name
            )
            old_sc_prototype = sc.prototype
            sc.prototype = new_sc_prototype
            sc.save()
            switch_config(sc, new_sc_prototype, old_sc_prototype)
        except Prototype.DoesNotExist:
            # sc.delete() ?!
            pass
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
    if upgrade.state_available:
        available = upgrade.state_available
        if obj.state in available:
            return True, ''
        elif available == 'any':
            return True, ''
        else:
            msg = '{} state "{}" is not in available states list: {}'
            return False, msg.format(obj.prototype.type, obj.state, available)
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
        res.append(upg)

    if order:
        if 'name' in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp))
        elif '-name' in order:
            return sorted(res, key=functools.cmp_to_key(rpm_cmp_reverse))
        else:
            return res
    else:
        return res


def do_upgrade(obj: Union[Cluster, HostProvider], upgrade: Upgrade) -> dict:
    old_proto = obj.prototype
    check_license(obj.prototype.bundle)
    check_license(upgrade.bundle)
    ok, msg = check_upgrade(obj, upgrade)
    if not ok:
        return err('UPGRADE_ERROR', msg)
    log.info('upgrade %s version %s (upgrade #%s)', obj_ref(obj), old_proto.version, upgrade.id)

    if obj.prototype.type == 'cluster':
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type='cluster')
    elif obj.prototype.type == 'provider':
        new_proto = Prototype.objects.get(bundle=upgrade.bundle, type='provider')
    else:
        return err('UPGRADE_ERROR', 'can upgrade only cluster or host provider')

    with transaction.atomic():
        obj.prototype = new_proto
        obj.state_before_upgrade = obj.state
        if upgrade.state_on_success:
            obj.state = upgrade.state_on_success
        obj.save()
        switch_config(obj, new_proto, old_proto)

        if obj.prototype.type == 'cluster':
            switch_services(upgrade, obj)
        elif obj.prototype.type == 'provider':
            switch_hosts(upgrade, obj)
        cm.issue.update_hierarchy_issues(obj)

    log.info('upgrade %s OK to version %s', obj_ref(obj), obj.prototype.version)
    cm.status_api.post_event(
        'upgrade', obj.prototype.type, obj.id, 'version', str(obj.prototype.version)
    )
    return {'id': obj.id, 'upgradable': bool(get_upgrade(obj))}
