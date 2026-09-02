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
from collections.abc import Collection
from dataclasses import dataclass

from cm.models import Cluster, Host, HostComponent
from cm.transition.status import StatusScenarios
from core.action import TaskMappingDelta
from core.cluster import ClusterService
from core.config import ConfigService
from core.types import ClusterID, HostName
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

from use_cases.transition.host.duplicate import create_duplicate


@dataclass(slots=True)
class ShareHostsOutcome:
    created: list[HostName]
    existing: list[HostName]


def share_cluster_hosts(
    source_cluster_id: ClusterID,
    target_cluster_id: ClusterID,
    config_service: ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> ShareHostsOutcome:
    """Duplicate every host of the source cluster into the target cluster.

    A fqdn already available to the target cluster (an original mapped there, or a duplicate
    made earlier) is reported as existing and left alone, so the operation is safe to re-run.
    """

    created: list[HostName] = []
    existing: list[HostName] = []

    target_fqdns = set(Host.objects.filter(cluster_id=target_cluster_id).values_list("fqdn", flat=True))

    for host_id, original_id, fqdn in (
        Host.objects.filter(cluster_id=source_cluster_id).order_by("fqdn").values_list("id", "original_id", "fqdn")
    ):
        if fqdn in target_fqdns:
            existing.append(fqdn)
            continue

        create_duplicate(
            config_service=config_service,
            # a source host may itself be a duplicate; the copy is always made from the original
            host_id=original_id or host_id,
            name=fqdn,
            rbac_scenarios=rbac_scenarios,
            status_scenarios=status_scenarios,
            cluster_id=target_cluster_id,
        )
        created.append(fqdn)

    return ShareHostsOutcome(created=created, existing=existing)


@dataclass(slots=True)
class UnshareHostsOutcome:
    removed: list[HostName]
    absent: list[HostName]


def unshare_cluster_hosts(
    target_cluster_id: ClusterID,
    fqdns: Collection[HostName],
    cluster_service: ClusterService,
    rbac_scenarios: RBACScenarios,
) -> UnshareHostsOutcome:
    """Unmap, remove and delete the duplicates the target cluster holds for the given fqdns.

    Only duplicates are ever touched: an original host belongs to its own cluster. Components
    still mapped on a duplicate are unmapped first, so cleanup also works when the step that
    should have unmapped them never ran. A fqdn without a duplicate here is reported as
    absent rather than failed, so cleanup can be re-run.
    """

    # imported lazily: `cm.legacy.api` transitively imports the module that runs internal
    # scripts, the same cycle `bundle_switch` breaks the same way
    from cm.legacy.api import delete_host, remove_host_from_cluster
    from cm.legacy.services.mapping import change_host_component_mapping_no_lock, check_nothing, lock_cluster_mapping

    duplicates = {
        host.fqdn: host
        for host in Host.objects.filter(cluster_id=target_cluster_id, original__isnull=False, fqdn__in=set(fqdns))
    }
    absent = sorted(set(fqdns) - set(duplicates))

    if not duplicates:
        return UnshareHostsOutcome(removed=[], absent=absent)

    bundle_id = Cluster.objects.values_list("prototype__bundle_id", flat=True).get(id=target_cluster_id)

    with atomic():
        lock_cluster_mapping(cluster_id=target_cluster_id)

        host_ids = {host.pk for host in duplicates.values()}
        to_unmap = defaultdict(set)
        for component_id, host_id in HostComponent.objects.filter(
            cluster_id=target_cluster_id, host_id__in=host_ids
        ).values_list("component_id", "host_id"):
            to_unmap[component_id].add(host_id)

        if to_unmap:
            change_host_component_mapping_no_lock(
                cluster_id=target_cluster_id,
                bundle_id=bundle_id,
                mapping_delta=TaskMappingDelta(remove=dict(to_unmap)),
                cluster_service=cluster_service,
                checks_func=check_nothing,
            )

        for host in duplicates.values():
            remove_host_from_cluster(host=host, cluster_service=cluster_service, rbac_scenarios=rbac_scenarios)
            delete_host(host=host, cluster_service=cluster_service, cancel_tasks=False)

    return UnshareHostsOutcome(removed=sorted(duplicates), absent=absent)
