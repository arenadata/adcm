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

from api_v2.host.serializers import HostChangeMaintenanceModeSerializer
from cm.adcm_config.config import init_object_config
from cm.api import check_license, load_service_map
from cm.api_context import CTX
from cm.errors import AdcmEx
from cm.issue import add_concern_to_object, update_hierarchy_issues
from cm.logger import logger
from cm.models import Cluster, Host, HostProvider, Prototype
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT

from adcm.permissions import check_custom_perm
from adcm.utils import get_maintenance_mode_response


def add_new_host_and_map_it(provider: HostProvider, fqdn: str, cluster: Cluster | None = None) -> Host:
    host_proto = Prototype.objects.get(type="host", bundle=provider.prototype.bundle)
    check_license(prototype=host_proto)
    with atomic():
        host = Host.objects.create(prototype=host_proto, provider=provider, fqdn=fqdn)
        obj_conf = init_object_config(proto=host_proto, obj=host)
        host.config = obj_conf
        if cluster:
            host.cluster = cluster

        host.save()
        add_concern_to_object(object_=host, concern=CTX.lock)

        update_hierarchy_issues(obj=host.provider)
        re_apply_object_policy(apply_object=provider)
        if cluster:
            re_apply_object_policy(apply_object=cluster)

    load_service_map()
    logger.info("host #%s %s is added", host.pk, host.fqdn)
    if cluster:
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host


def maintenance_mode(request, **kwargs):
    host = Host.obj.filter(pk=kwargs["pk"]).first()

    if not host:
        raise AdcmEx(code="HOST_NOT_FOUND")

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

    response: Response = get_maintenance_mode_response(obj=host, serializer=serializer)
    if response.status_code == HTTP_200_OK:
        response.data = serializer.data

    return response
