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

from collections import defaultdict
from functools import wraps

from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.cluster.types import ObjectMaintenanceModeState
from requests import Response

from cm.models import Cluster, Host, HostComponent, Service, ServiceComponent
from cm.services.cluster import (
    retrieve_clusters_objects_maintenance_mode,
    retrieve_clusters_topology,
)
from cm.status_api import api_request


def reset_hc_map() -> None:
    """Send request to SS with new HC map of all clusters"""
    comps = defaultdict(lambda: defaultdict(list))
    hosts = defaultdict(list)
    hc_map = {}
    services = defaultdict(list)

    for cluster_id, service_id, component_id, host_id in (
        HostComponent.objects.values_list("cluster_id", "service_id", "component_id", "host_id")
        .exclude(
            component_id__in=ServiceComponent.objects.values_list("id", flat=True).filter(
                prototype__monitoring="passive"
            )
        )
        .order_by("id")
    ):
        key = f"{host_id}.{component_id}"
        hc_map[key] = {"cluster": cluster_id, "service": service_id}
        comps[str(cluster_id)][str(service_id)].append(key)

    for host_id, cluster_id in Host.objects.values_list("id", "cluster_id").filter(prototype__monitoring="active"):
        hosts[cluster_id or 0].append(host_id)

    for service_id, cluster_id in Service.objects.values_list("id", "cluster_id").filter(
        prototype__monitoring="active"
    ):
        services[cluster_id].append(service_id)

    data = {
        "hostservice": hc_map,
        "component": comps,
        "service": services,
        "host": hosts,
    }
    api_request(method="post", url="servicemap/", data=data)


def reset_objects_in_mm() -> Response | None:
    """Send request to SS with all objects that are currently in MM"""
    cluster_ids = set(Cluster.objects.values_list("id", flat=True).filter(prototype__allow_maintenance_mode=True))
    if not cluster_ids:
        return None

    service_ids = set()
    component_ids = set()
    host_ids = set()

    mm_info = retrieve_clusters_objects_maintenance_mode(cluster_ids=cluster_ids)

    for topology in retrieve_clusters_topology(cluster_ids=cluster_ids):
        cluster_objects_mm = calculate_maintenance_mode_for_cluster_objects(
            topology=topology, own_maintenance_mode=mm_info
        )
        service_ids |= {
            entry_id for entry_id, mm in cluster_objects_mm.services.items() if mm == ObjectMaintenanceModeState.ON
        }
        component_ids |= {
            entry_id for entry_id, mm in cluster_objects_mm.components.items() if mm == ObjectMaintenanceModeState.ON
        }
        host_ids |= {
            entry_id for entry_id, mm in cluster_objects_mm.hosts.items() if mm == ObjectMaintenanceModeState.ON
        }

    return api_request(
        method="post",
        url="object/mm/",
        data={
            "services": list(service_ids),
            "components": list(component_ids),
            "hosts": list(host_ids),
        },
    )


def update_mm_objects(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        reset_objects_in_mm()
        return res

    return wrapper
