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

from django.db import transaction
from version_utils import rpm

import cm.config as config
import cm.issue
import cm.status_api
from cm.adcm_config import proto_ref, obj_ref, switch_config
from cm.errors import raise_AdcmEx as err
from cm.logger import log
from cm.models import (
    Prototype, Component, Host, HostComponent, ServiceComponent, PrototypeImport,
    ClusterBind, ClusterObject, Upgrade
)


def check_license(bundle):
    if bundle.license == 'unaccepted':
        msg = 'License for bundle "{}" {} {} is not accepted'
        err('LICENSE_ERROR', msg.format(bundle.name, bundle.version, bundle.edition))


def version_in(version, ver):
    # log.debug('version_in: %s < %s > %s', ver.min_version, version, ver.max_version)
    if ver.min_strict:
        if rpm.compare_versions(version, ver.min_version) <= 0:
            return False
    else:
        if rpm.compare_versions(version, ver.min_version) < 0:
            return False
    if ver.max_strict:
        if rpm.compare_versions(version, ver.max_version) >= 0:
            return False
    else:
        if rpm.compare_versions(version, ver.max_version) > 0:
            return False
    return True


def switch_service(co, new_proto):
    log.info('upgrade switch from %s to %s', proto_ref(co.prototype), proto_ref(new_proto))
    switch_config(co, new_proto, co.prototype)
    co.prototype = new_proto
    co.save()


def switch_components(cluster, co, new_co_proto):
    for sc in ServiceComponent.objects.filter(cluster=cluster, service=co):
        try:
            comp = Component.objects.get(prototype=new_co_proto, name=sc.component.name)
            sc.component = comp
            sc.save()
        except Component.DoesNotExist:
            # sc.delete() ?!
            pass
    for comp in Component.objects.filter(prototype=new_co_proto):
        try:
            ServiceComponent.objects.get(cluster=cluster, service=co, component=comp)
        except ServiceComponent.DoesNotExist:
            sc = ServiceComponent(cluster=cluster, service=co, component=comp)
            sc.save()


def check_upgrade_version(obj, upgrade):
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


def check_upgrade_edition(obj, upgrade):
    if not upgrade.from_edition:
        return True, ''
    from_edition = upgrade.from_edition
    if obj.prototype.bundle.edition not in from_edition:
        msg = 'bundle edition "{}" is not in upgrade list: {}'
        return False, msg.format(obj.prototype.bundle.edition, from_edition)
    return True, ''


def check_upgrade_state(obj, upgrade):
    if obj.state == config.Job.LOCKED:
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


def check_upgrade_import(obj, upgrade):   # pylint: disable=too-many-branches
    def get_export(cbind):
        if cbind.source_service:
            return cbind.source_service
        else:
            return cbind.source_cluster

    def get_import(cbind):   # pylint: disable=redefined-outer-name
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
                return (False, msg.format(
                    export.prototype.name, proto_ref(proto), pi.min_version, pi.max_version,
                    export.prototype.version, obj_ref(export)
                ))
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
            return (False, msg.format(
                proto_ref(proto), pi.min_version, pi.max_version, obj_ref(import_obj)
            ))

    return True, ''


def check_upgrade(obj, upgrade):
    issue = cm.issue.get_issue(obj)
    if not cm.issue.issue_to_bool(issue):
        return False, '{} has issue: {}'.format(obj_ref(obj), issue)

    check_list = [
        check_upgrade_version, check_upgrade_edition, check_upgrade_state, check_upgrade_import
    ]
    for func in check_list:
        ok, msg = func(obj, upgrade)
        if not ok:
            return False, msg
    return True, ''


def switch_hc(obj, upgrade):
    def find_service(service, bundle):
        try:
            return Prototype.objects.get(bundle=bundle, type='service', name=service.prototype.name)
        except Prototype.DoesNotExist:
            return None

    def find_component(component, proto):
        try:
            return Component.objects.get(prototype=proto, name=component.component.name)
        except Component.DoesNotExist:
            return None

    if obj.prototype.type == 'host':
        return
    for hc in HostComponent.objects.filter(cluster=obj):
        service_proto = find_service(hc.service, upgrade.bundle)
        if not service_proto:
            hc.delete()
            continue
        if not find_component(hc.component, service_proto):
            hc.delete()
            continue


def get_upgrade(obj, order=None):
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


def do_upgrade(obj, upgrade):
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
        if upgrade.state_on_success:
            obj.state = upgrade.state_on_success
        obj.save()
        switch_config(obj, new_proto, old_proto)

        if obj.prototype.type == 'cluster':
            for p in Prototype.objects.filter(bundle=upgrade.bundle, type='service'):
                try:
                    co = ClusterObject.objects.get(cluster=obj, prototype__name=p.name)
                    switch_service(co, p)
                    switch_components(obj, co, p)
                except ClusterObject.DoesNotExist:
                    # co.delete() ?!
                    pass
            switch_hc(obj, upgrade)
        elif obj.prototype.type == 'provider':
            for p in Prototype.objects.filter(bundle=upgrade.bundle, type='host'):
                for host in Host.objects.filter(provider=obj, prototype__name=p.name):
                    switch_service(host, p)
        cm.issue.save_issue(obj)

    log.info('upgrade %s OK to version %s', obj_ref(obj), obj.prototype.version)
    cm.status_api.post_event(
        'upgrade', obj.prototype.type, obj.id, 'version', str(obj.prototype.version)
    )
    return {'id': obj.id, 'upgradable': bool(get_upgrade(obj))}
