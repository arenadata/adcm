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
from cm.adcm_config.config import init_object_config
from cm.api import check_license
from cm.issue import (
    _prototype_issue_map,
    add_concern_to_object,
    recheck_issues,
)
from cm.logger import logger
from cm.models import Cluster, Host, ObjectType, Prototype
from cm.services.concern import retrieve_issue
from cm.services.concern.locks import get_lock_on_object
from cm.services.maintenance_mode import get_maintenance_mode_response
from cm.services.status.notify import reset_hc_map
from core.types import ADCMCoreType, BundleID, CoreObjectDescriptor, ProviderID
from rbac.models import re_apply_object_policy
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT

from api_v2.host.serializers import HostChangeMaintenanceModeSerializer


def create_host(bundle_id: BundleID, provider_id: ProviderID, fqdn: str, cluster: Cluster | None) -> Host:
    host_prototype = Prototype.objects.get(type=ObjectType.HOST, bundle_id=bundle_id)
    check_license(prototype=host_prototype)

    host = Host.objects.create(prototype=host_prototype, provider_id=provider_id, fqdn=fqdn, cluster=cluster)

    process_config_issues_policies_hc(host)

    return host


def _recheck_new_host_issues(host: Host):
    """
    Copy-pasted parts of update_hierarchy_issues() from cm.issue for the sake of number of queries optimization
    Works only on newly created hosts (without mapping to components)
    """

    recheck_issues(obj=host)  # only host itself is directly affected

    # propagate issues from provider only to this host
    provider = CoreObjectDescriptor(id=host.provider_id, type=ADCMCoreType.PROVIDER)
    for issue_cause in _prototype_issue_map.get(ObjectType.PROVIDER, []):
        add_concern_to_object(object_=host, concern=retrieve_issue(owner=provider, cause=issue_cause))


def process_config_issues_policies_hc(host: Host) -> None:
    obj_conf = init_object_config(proto=host.prototype, obj=host)
    host.config = obj_conf
    host.save(update_fields=["config"])

    add_concern_to_object(object_=host, concern=get_lock_on_object(host.provider))
    _recheck_new_host_issues(host=host)
    re_apply_object_policy(apply_object=host.provider)

    if cluster := host.cluster:
        re_apply_object_policy(apply_object=cluster)

    reset_hc_map()

    if cluster:
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)
    else:
        logger.info("host #%s %s is added", host.pk, host.fqdn)


def maintenance_mode(request: Request, host: Host) -> Response:
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

    response = get_maintenance_mode_response(obj=host, serializer=serializer)
    if response.status_code == HTTP_200_OK:
        response.data = serializer.data

    return response
