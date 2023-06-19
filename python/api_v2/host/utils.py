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

from cm.adcm_config.config import init_object_config
from cm.api import check_license, load_service_map
from cm.api_context import CTX
from cm.issue import update_hierarchy_issues
from cm.logger import logger
from cm.models import Cluster, Host, HostProvider, Prototype
from cm.status_api import post_event
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy


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
        host.add_to_concerns(CTX.lock)
        update_hierarchy_issues(obj=host.provider)
        re_apply_object_policy(apply_object=provider)
        if cluster:
            re_apply_object_policy(apply_object=cluster)

    CTX.event.send_state()
    post_event(
        event="create", object_id=host.pk, object_type="host", details={"type": "provider", "value": str(provider.pk)}
    )
    load_service_map()
    logger.info("host #%s %s is added", host.pk, host.fqdn)
    if cluster:
        post_event(
            event="add", object_id=host.pk, object_type="host", details={"type": "cluster", "value": str(cluster.pk)}
        )
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host


def map_list_of_hosts(hosts, cluster):
    for host in hosts:
        host.cluster = cluster
        host.save(update_fields=["cluster"])
        host.add_to_concerns(CTX.lock)
        update_hierarchy_issues(host)
        post_event(
            event="add", object_id=host.pk, object_type="host", details={"type": "cluster", "value": str(cluster.pk)}
        )
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    re_apply_object_policy(cluster)
    load_service_map()
    return hosts
