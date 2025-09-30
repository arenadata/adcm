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

from cm import converters
from cm.api import check_license
from cm.errors import AdcmEx
from cm.models import Cluster, ConcernCause, Host, Prototype, Provider
from cm.services import config_service as config
from cm.services.concern._operations import create_issue
from cm.services.concern.cases import recalculate_own_concerns_on_add_hosts
from cm.services.concern.checks import object_configuration_has_issue
from cm.services.concern.distribution import (
    distribute_concern_from_provider_to_host,
    distribute_concern_on_related_objects,
)
from cm.services.status.notify import reset_hc_map
from cm.status_api import notify_about_new_concern, notify_about_redistributed_concerns_from_maps
from core.types import ADCMCoreType
from django.conf import settings
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy


def create_hostprovider(prototype: Prototype, name: str, description: str) -> Provider:
    if prototype.type != ADCMCoreType.PROVIDER.value:
        raise AdcmEx("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {prototype.type}")

    check_license(prototype)

    with atomic():
        provider = Provider.objects.create(prototype=prototype, name=name, description=description)
        config.create.initial_config_if_required(provider, files_dir=settings.FILE_DIR)

        provider_cod = converters.orm_object_to_core_descriptor(provider)
        concern_id = None
        related_objects = {}
        if object_configuration_has_issue(provider):
            concern = create_issue(owner=provider_cod, cause=ConcernCause.CONFIG)
            concern_id = concern.pk
            related_objects = distribute_concern_on_related_objects(owner=provider_cod, concern_id=concern_id)

    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return provider


def create_host(hostprovider: Provider, name: str, cluster: Cluster | None) -> Host:
    with atomic():
        bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=hostprovider.prototype_id)  # pyright: ignore [reportAttributeAccessIssue]
        host_prototype = Prototype.objects.get(type=ADCMCoreType.HOST.value, bundle_id=bundle_id)

        check_license(prototype=host_prototype)

        host = Host.objects.create(prototype=host_prototype, provider_id=hostprovider.pk, fqdn=name, cluster=cluster)

        config.create.initial_config_if_required(owner_object=host, files_dir=settings.FILE_DIR)

        concern_map = {ADCMCoreType.HOST: {host.pk: set()}}
        host_concern_map = recalculate_own_concerns_on_add_hosts(host=host)
        if host_concern_map:
            concern_id = next(iter(host_concern_map[ADCMCoreType.HOST][host.pk]))
            host.concerns.add(concern_id)
            concern_map[ADCMCoreType.HOST][host.pk].add(concern_id)

        attached_concern_map = distribute_concern_from_provider_to_host(host_id=host.pk)
        if attached_concern_map:
            concern_map[ADCMCoreType.HOST][host.pk] |= attached_concern_map[ADCMCoreType.HOST][host.pk]

        re_apply_object_policy(apply_object=host.provider)

        if cluster := host.cluster:
            re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=concern_map, removed={})

    return host
