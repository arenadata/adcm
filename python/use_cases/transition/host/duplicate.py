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
from dataclasses import dataclass
from typing import TypeAlias, cast

from cm.errors import AdcmEx
from cm.legacy.services import cluster
from cm.legacy.services.concern.distribution import distribute_concern_from_provider_to_hosts
from cm.legacy.services.host import repo
from cm.models import Cluster, Host
from cm.transition.status import StatusScenarios
from core.config import ConfigService
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor, Descriptor, HostDesc, HostID, HostName
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

from use_cases.errors import UseCaseError

HostDuplicateID: TypeAlias = HostID


@dataclass(slots=True)
class CreateHostDuplicates:
    """Give clusters copies of the given original hosts, in a fixed number of queries.

    Every step the one-host API performs per host - the row insert, joining the
    cluster (with the policy re-application and the host-component concern it
    triggers) and the provider concerns - is performed once for the whole set,
    so the query count depends on the number of prototypes involved and not on
    the number of hosts. Only the file-type symlinks remain per host, and those
    are filesystem work, not queries.

    The originals must be originals: a duplicate of a duplicate is not a thing
    ADCM has, and callers resolve `original_id or id` before getting here.
    """

    config_service: ConfigService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios

    def __call__(
        self,
        originals: Sequence[Host],
        cluster_id: ClusterID | None = None,
        names: Sequence[HostName] | None = None,
    ) -> list[Host]:
        if not originals:
            return []

        if names is not None and len(names) != len(originals):
            message = f"Duplicate names: was given {len(names)} for {len(originals)} originals"
            raise ValueError(message)

        with atomic():
            duplicates = [
                repo.build_duplicate_host_record(
                    host=original,
                    overrides=repo.DuplicateHostOverrides(
                        name=name or original.fqdn, description=f"Copied from {original.fqdn}"
                    ),
                )
                for original, name in zip(originals, names or [None] * len(originals), strict=True)
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
                    specification = self.config_service.retrieve_specification(
                        owner=CoreObjectDescriptor(id=representative.pk, type=ADCMCoreType.HOST)
                    )
                    self.config_service.prepare_symlinks_for_file_type_of_many(
                        specification=specification,
                        pairs=(
                            (
                                cast(HostDesc, Descriptor(id=original.pk, type=ADCMCoreType.HOST)),
                                cast(HostDesc, Descriptor(id=duplicate.pk, type=ADCMCoreType.HOST)),
                            )
                            for original, duplicate in pairs
                        ),
                    )

            if cluster_id is not None:
                try:
                    cluster.perform_host_to_cluster_map(
                        cluster_id=cluster_id,
                        hosts=[duplicate.pk for duplicate in duplicates],
                        status_service=self.status_scenarios,
                        rbac_scenarios=self.rbac_scenarios,
                    )
                except Cluster.DoesNotExist as e:
                    raise UseCaseError(f"Cluster #{cluster_id} does not exist") from e

            attached_concern_map = distribute_concern_from_provider_to_hosts(
                host_ids=[duplicate.pk for duplicate in duplicates]
            )

        duplicates_of_original = defaultdict(list)
        for original, duplicate in zip(originals, duplicates, strict=True):
            duplicates_of_original[original.pk].append(duplicate.pk)

        for original_id, duplicate_ids in duplicates_of_original.items():
            self.status_scenarios.register_host_duplicates(original=original_id, duplicates=duplicate_ids)

        self.status_scenarios.notify_about_redistributed_concerns_from_maps(added=attached_concern_map, removed={})

        return list(duplicates)


def create_duplicate(
    config_service: ConfigService,
    host_id: HostID,
    name: HostName,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
    cluster_id: ClusterID | None = None,
) -> HostDuplicateID:
    """The one-host form of `CreateHostDuplicates`, kept for the host duplicates API."""

    try:
        original = repo.get_original_host(host_id=host_id)
    except Host.DoesNotExist as e:
        raise AdcmEx(code="INVALID_CREATE_DUPLICATE_HOST", msg=f"There is not a #{host_id} original host") from e

    try:
        duplicate = CreateHostDuplicates(
            config_service=config_service,
            rbac_scenarios=rbac_scenarios,
            status_scenarios=status_scenarios,
        )(originals=[original], cluster_id=cluster_id, names=[name])[0]
    except UseCaseError as e:
        # the duplicates API answered a missing cluster with this code before the bulk use case existed
        raise AdcmEx("CLUSTER_NOT_FOUND") from e

    return duplicate.pk
