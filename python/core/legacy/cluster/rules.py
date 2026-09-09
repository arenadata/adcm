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
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from operator import attrgetter
from typing import Literal

from core.legacy.cluster.errors import (
    ClusterAddHostError,
    HostAlreadyBoundError,
    HostBelongsToAnotherClusterError,
    HostDoesNotExistError,
)
from core.legacy.cluster.types import HostAddInfo
from core.types import ClusterID, HostID, HostName


@dataclass(slots=True, frozen=True)
class HostCandidateDTO:
    cluster_id: ClusterID
    in_cluster: list[HostAddInfo]
    candidates: list[HostAddInfo]


class CandidateViolationType(str, Enum):
    DUPLICATE_NAME = "duplicate-name"
    DUPLICATE_ORIGIN = "duplicate-origin"

    BOUND_SAME = "bound-same"
    BOUND_ANOTHER = "bound-another"


@dataclass(slots=True)
class CandidateViolation:
    host: HostAddInfo
    type: CandidateViolationType
    level: Literal["added", "candidates"]
    """
    Where the conflict lies: strictly within candidates or with already added hosts.
    This distinction is required for filtering from user's code since some cases may ignore it.
    """


def check_all_hosts_exist(hosts_to_add: Collection[int], existing_hosts: Collection[HostAddInfo]) -> None:
    if not set(hosts_to_add).issubset(map(attrgetter("id"), existing_hosts)):
        raise HostDoesNotExistError()


def check_hosts_can_be_added_to_cluster(payload: HostCandidateDTO) -> None:
    """
    Raise error if some of candidates can't be added to cluster.
    """

    violations = find_host_candidate_violations(payload)
    if not violations:
        return

    error = _construct_host_add_violation_error(violations)
    raise error


def detect_valid_host_candidates(payload: HostCandidateDTO) -> list[HostAddInfo]:
    """
    Return candidates that won't violate cluster's host restrictions if added ONE BY ONE.
    """

    violations = find_host_candidate_violations(payload)

    if not violations:
        return payload.candidates

    hosts_with_violations = {violation.host.id for violation in violations if violation.level == "added"}
    return [host for host in payload.candidates if host.id not in hosts_with_violations]


def find_host_candidate_violations(payload: HostCandidateDTO) -> list[CandidateViolation]:
    """
    Analyze given "state" from payload assuming all the candidates will be added to already current cluster hosts
    returning all potential violations that come if such assumption come true.
    """

    return _find_host_duplicates_violations(payload) + _find_host_cluster_violations(payload)


def _find_host_duplicates_violations(payload: HostCandidateDTO) -> list[CandidateViolation]:
    duplicates_index: dict[
        tuple[Literal[CandidateViolationType.DUPLICATE_ORIGIN], HostID]
        | tuple[Literal[CandidateViolationType.DUPLICATE_NAME], HostName],
        set[HostAddInfo],
    ] = defaultdict(set)
    for host in payload.candidates + payload.in_cluster:
        duplicates_index[CandidateViolationType.DUPLICATE_ORIGIN, host.original_id or host.id].add(host)
        duplicates_index[CandidateViolationType.DUPLICATE_NAME, host.name].add(host)

    in_cluster: set[HostID | HostName] = set(
        chain.from_iterable((host.original_id or host.id, host.name) for host in payload.in_cluster)
    )
    candidates_ids = {host.id for host in payload.candidates}

    violations = []

    for (violation_type, value), hosts_with_same_value in duplicates_index.items():
        has_duplicates = len(hosts_with_same_value) > 1
        if not has_duplicates:
            continue

        violation_level = "added" if value in in_cluster else "candidates"

        for host in hosts_with_same_value:
            if host.id in candidates_ids:
                violation = CandidateViolation(host=host, type=violation_type, level=violation_level)
                violations.append(violation)

    return violations


def _find_host_cluster_violations(payload: HostCandidateDTO) -> list[CandidateViolation]:
    candidates_with_cluster = filter(lambda host: host.cluster_id is not None, payload.candidates)
    return [
        CandidateViolation(
            type=(
                CandidateViolationType.BOUND_ANOTHER
                if payload.cluster_id != candidate.cluster_id
                else CandidateViolationType.BOUND_SAME
            ),
            level="candidates",
            host=candidate,
        )
        for candidate in candidates_with_cluster
    ]


def _construct_host_add_violation_error(violations: list[CandidateViolation]) -> Exception:
    violation_type = violations[0].type  # raise first violation
    hosts = tuple(violation.host for violation in violations if violation.type == violation_type)

    match violation_type:
        case CandidateViolationType.DUPLICATE_NAME:
            hosts_repr = _format_violation_hosts(hosts)
            msg = f"Host with the same name is already added to cluster. Errors: {hosts_repr}"
            return ClusterAddHostError(msg)

        case CandidateViolationType.DUPLICATE_ORIGIN:
            hosts_repr = _format_violation_hosts(hosts)
            msg = f"Only one copy of a host can be added to the cluster. Errors: {hosts_repr}"
            return ClusterAddHostError(msg)

        case CandidateViolationType.BOUND_ANOTHER:
            return HostBelongsToAnotherClusterError()

        case CandidateViolationType.BOUND_SAME:
            return HostAlreadyBoundError()


def _format_violation_hosts(hosts: Iterable[HostAddInfo]) -> str:
    return ", ".join(sorted(f"<Host #{host.id} {host.name}>" for host in hosts))
