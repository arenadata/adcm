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
from collections.abc import Sequence
from typing import TypeAlias, cast

from cm.errors import AdcmEx
from cm.legacy.services import cluster
from cm.legacy.services.concern.distribution import (
    distribute_concern_from_provider_to_host,
    distribute_concern_from_provider_to_hosts,
)
from cm.legacy.services.host import repo
from cm.models import Cluster, Host
from cm.transition.status import StatusScenarios
from core.config import ConfigService
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor, Descriptor, HostDesc, HostID, HostName
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

HostDuplicateID: TypeAlias = HostID


def create_duplicate(
    config_service: ConfigService,
    host_id: HostID,
    name: HostName,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
    cluster_id: ClusterID | None = None,
) -> HostDuplicateID:
    with atomic():
        try:
            original = repo.get_original_host(host_id=host_id)
        except Host.DoesNotExist as e:
            raise AdcmEx(code="INVALID_CREATE_DUPLICATE_HOST", msg=f"There is not a #{host_id} original host") from e

        overrides = repo.DuplicateHostOverrides(name=name, description=f"Copied from {original.fqdn}")
        duplicate = repo.duplicate_host_record(host=original, overrides=overrides)

        if original.config:
            original_desc = cast(HostDesc, Descriptor(id=original.pk, type=ADCMCoreType.HOST))
            duplicate_desc = cast(HostDesc, Descriptor(id=duplicate.pk, type=ADCMCoreType.HOST))
            config_service.prepare_symlinks_for_file_type(original=original_desc, duplicate=duplicate_desc)

        if cluster_id is not None:
            try:
                cluster.perform_host_to_cluster_map(
                    cluster_id=cluster_id,
                    hosts=[duplicate.pk],
                    status_service=status_scenarios,
                    rbac_scenarios=rbac_scenarios,
                )
            except Cluster.DoesNotExist as e:
                raise AdcmEx("CLUSTER_NOT_FOUND") from e

        attached_concern_map = distribute_concern_from_provider_to_host(host_id=duplicate.pk)

    status_scenarios.register_host_duplicates(original=host_id, duplicates=(duplicate.pk,))
    status_scenarios.notify_about_redistributed_concerns_from_maps(added=attached_concern_map, removed={})

    return duplicate.pk


def create_duplicates(
    config_service: ConfigService,
    originals: Sequence[Host],
    cluster_id: ClusterID,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> list[Host]:
    """Duplicate every given original host into the cluster, in a fixed number of queries.

    The batched form of `create_duplicate`. Every step that `create_duplicate` performs per
    host - the row insert, joining the cluster (with the policy re-application and the
    host-component concern it triggers) and the provider concerns - is performed here once for
    the whole set, so the query count depends on the number of prototypes involved and not on
    the number of hosts. Only the file-type symlinks remain per host, and those are filesystem
    work, not queries.

    The originals must be originals: a duplicate of a duplicate is not a thing ADCM has, and
    callers resolve `original_id or id` before getting here.
    """

    if not originals:
        return []

    duplicates = [
        repo.build_duplicate_host_record(
            host=original,
            overrides=repo.DuplicateHostOverrides(name=original.fqdn, description=f"Copied from {original.fqdn}"),
        )
        for original in originals
    ]
    Host.objects.bulk_create(duplicates)

    originals_with_config = [
        (original, duplicate)
        for original, duplicate in zip(originals, duplicates, strict=True)
        if original.config_id  # pyright: ignore[reportAttributeAccessIssue]
    ]
    if originals_with_config:
        by_prototype = defaultdict(list)
        for original, duplicate in originals_with_config:
            by_prototype[original.prototype_id].append((original, duplicate))  # pyright: ignore[reportAttributeAccessIssue]

        for pairs in by_prototype.values():
            representative = pairs[0][0]
            specification = config_service.retrieve_specification(
                owner=CoreObjectDescriptor(id=representative.pk, type=ADCMCoreType.HOST)
            )
            config_service.prepare_symlinks_for_file_type_of_many(
                specification=specification,
                pairs=(
                    (
                        cast(HostDesc, Descriptor(id=original.pk, type=ADCMCoreType.HOST)),
                        cast(HostDesc, Descriptor(id=duplicate.pk, type=ADCMCoreType.HOST)),
                    )
                    for original, duplicate in pairs
                ),
            )

    try:
        cluster.perform_host_to_cluster_map(
            cluster_id=cluster_id,
            hosts=[duplicate.pk for duplicate in duplicates],
            status_service=status_scenarios,
            rbac_scenarios=rbac_scenarios,
        )
    except Cluster.DoesNotExist as e:
        raise AdcmEx("CLUSTER_NOT_FOUND") from e

    attached_concern_map = distribute_concern_from_provider_to_hosts(
        host_ids=[duplicate.pk for duplicate in duplicates]
    )

    duplicates_of_original = defaultdict(list)
    for original, duplicate in zip(originals, duplicates, strict=True):
        duplicates_of_original[original.pk].append(duplicate.pk)

    for original_id, duplicate_ids in duplicates_of_original.items():
        status_scenarios.register_host_duplicates(original=original_id, duplicates=duplicate_ids)

    status_scenarios.notify_about_redistributed_concerns_from_maps(added=attached_concern_map, removed={})

    return duplicates
