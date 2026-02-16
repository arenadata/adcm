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

from adcm.permissions import check_custom_perm
from cm.legacy.adcm_config.config import init_object_config
from cm.legacy.api import check_license
from cm.legacy.services.concern.cases import recalculate_own_concerns_on_add_hosts
from cm.legacy.services.concern.distribution import distribute_concern_from_provider_to_host
from cm.legacy.services.maintenance_mode import get_maintenance_mode_response
from cm.legacy.services.status.notify import reset_hc_map
from cm.legacy.status_api import notify_about_redistributed_concerns_from_maps
from cm.logger import logger
from cm.models import Cluster, Host, ObjectType, Prototype
from core.types import ADCMCoreType, BundleID, ProviderID
from rbac.models import re_apply_object_policy
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT
from use_cases.transition.job.schedule import ScheduleTask

from api_v2.host.serializers import HostChangeMaintenanceModeSerializer


def create_host(bundle_id: BundleID, provider_id: ProviderID, fqdn: str, cluster: Cluster | None) -> Host:
    host_prototype = Prototype.objects.get(type=ObjectType.HOST, bundle_id=bundle_id)
    check_license(prototype=host_prototype)

    host = Host.objects.create(prototype=host_prototype, provider_id=provider_id, fqdn=fqdn, cluster=cluster)

    obj_conf = init_object_config(proto=host.prototype, obj=host)
    host.config = obj_conf
    host.save(update_fields=["config"])

    concern_map = {ADCMCoreType.HOST: {host.id: set()}}
    host_concern_map = recalculate_own_concerns_on_add_hosts(host=host)

    if host_concern_map:
        concern_id = next(iter(host_concern_map[ADCMCoreType.HOST][host.id]))
        host.concerns.add(concern_id)
        concern_map[ADCMCoreType.HOST][host.id].add(concern_id)

    attached_concern_map = distribute_concern_from_provider_to_host(host_id=host.id)

    if attached_concern_map:
        concern_map[ADCMCoreType.HOST][host.id] |= attached_concern_map[ADCMCoreType.HOST][host.id]

    re_apply_object_policy(apply_object=host.provider)

    if cluster := host.cluster:
        re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=concern_map, removed={})

    if cluster:
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)
    else:
        logger.info("host #%s %s is added", host.pk, host.fqdn)

    return host


def maintenance_mode(request: Request, host: Host, schedule_task: ScheduleTask) -> Response:
    check_custom_perm(user=request.user, action_type="change_maintenance_mode", model="host", obj=host)

    serializer = HostChangeMaintenanceModeSerializer(instance=host, data=request.data)
    serializer.is_valid(raise_exception=True)
    if not host.is_maintenance_mode_available:
        return Response(
            data={
                "code": "MAINTENANCE_MODE_NOT_AVAILABLE",
                "level": "error",
                "desc": "Maintenance mode is not available",
            },
            status=HTTP_409_CONFLICT,
        )

    response = get_maintenance_mode_response(obj=host, serializer=serializer, schedule_task=schedule_task)
    if response.status_code == HTTP_200_OK:
        response.data = serializer.data

    return response
