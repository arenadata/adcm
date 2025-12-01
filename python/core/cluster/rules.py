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
from dataclasses import dataclass
from enum import Enum
from itertools import chain, filterfalse
from operator import attrgetter
from typing import Collection

from typing_extensions import Self

from core.cluster.errors import (
    ClusterAddHostError,
    HostAlreadyBoundError,
    HostBelongsToAnotherClusterError,
    HostDoesNotExistError,
)
from core.cluster.types import HostAddInfo
from core.result import Fail, Success
from core.types import ClusterID, HostID


@dataclass(slots=True, frozen=True)
class HostCandidateDTO:
    cluster_id: ClusterID
    in_cluster: list[HostAddInfo]
    candidates: list[HostAddInfo]

    def find_by_ids(self: Self, ids: Collection[HostID]) -> list[HostAddInfo]:
        return [host for host in self.candidates + self.in_cluster if host.id in ids]


class _ViolationType(str, Enum):
    NAME = "name"
    DUPLICATE = "duplicate"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    ALREADY_BOUND = "already_bound"
    FOREIGN_CLUSTER = "foreign_cluster"


@dataclass(slots=True, frozen=True)
class _Violation:
    type: _ViolationType
    hosts: list[HostAddInfo]

    def find_by_ids(self: Self, ids: Collection[HostID]) -> list[HostAddInfo]:
        return [host for host in self.hosts if host.id in ids]

    @property
    def host_ids(self: Self) -> set[HostID]:
        return {host.id for host in self.hosts}

    @property
    def hosts_repr(self: Self) -> str:
        repr_ = sorted(f"<Host #{host.id} {host.name}>" for host in self.hosts)

        return ", ".join(repr_)


def check_all_hosts_exist(hosts_to_add: Collection[int], existing_hosts: Collection[HostAddInfo]) -> None:
    if not set(hosts_to_add).issubset(map(attrgetter("id"), existing_hosts)):
        raise HostDoesNotExistError()


def check_hosts_can_be_added_to_cluster(payload: HostCandidateDTO) -> None:
    result = _find_host_in_cluster_violations(payload)
    match result:
        case Fail(value=violations):
            candidates = {host.id for host in payload.candidates}
            violations_ = []
            for violation in violations:
                if violation.type != _ViolationType.DUPLICATE:
                    violations_.append(violation)
                else:
                    hosts_within_candidates = violation.host_ids.intersection(candidates)
                    if hosts_within_candidates:
                        hosts = violation.find_by_ids(hosts_within_candidates)
                        violations_.append(_Violation(type=violation.type, hosts=hosts))

            if not violations_:
                return

            violation = violations_[0]  # raise first violation

            match violation.type:
                case _ViolationType.NAME:
                    msg = f"Host with the same name is already added to cluster. Errors: {violation.hosts_repr}"
                    raise ClusterAddHostError(msg)

                case _ViolationType.DUPLICATE | _ViolationType.DUPLICATE_CANDIDATE:
                    msg = f"Only one copy of a host can be added to the cluster. Errors: {violation.hosts_repr}"
                    raise ClusterAddHostError(msg)

                case _ViolationType.FOREIGN_CLUSTER:
                    raise HostBelongsToAnotherClusterError()

                case _ViolationType.ALREADY_BOUND:
                    raise HostAlreadyBoundError()

                case _:
                    raise NotImplementedError(f"Unexpected violation type: {violation.type}")


def filter_host_candidates(payload: HostCandidateDTO) -> list[HostAddInfo]:
    result = _find_host_in_cluster_violations(payload)
    match result:
        case Success(None):
            return payload.candidates

        case Fail(value=violations):
            violations = tuple(filterfalse(lambda v: v.type == _ViolationType.DUPLICATE_CANDIDATE, violations))
            violation_ids = set(chain.from_iterable(v.host_ids for v in violations))

            return [host for host in payload.candidates if host.id not in violation_ids]


def _find_host_in_cluster_violations(payload: HostCandidateDTO) -> Success[None] | Fail[list[_Violation]]:
    finders = (
        _find_host_duplicates_violations,
        _find_host_cluster_violations,
        _find_host_names_violations,
    )

    violations = []
    for finder in finders:
        violations.extend(finder(payload))

    if violations:
        return Fail(violations)

    return Success(None)


def _find_host_duplicates_violations(payload: HostCandidateDTO) -> list[_Violation]:
    in_cluster_originals = {host.original_id or host.id for host in payload.in_cluster}

    all_ids = set()
    original_duplicates_map = defaultdict(set)
    for host in payload.candidates + payload.in_cluster:
        all_ids.add(host.id)
        if host.original_id:
            original_duplicates_map[host.original_id].add(host.id)

    hosts: list[HostAddInfo] = []
    hosts_candidates_violations = []

    for original_id, duplicate_ids in original_duplicates_map.items():
        dupe_ids_group = {id_ for id_ in (original_id, *duplicate_ids) if id_ in all_ids}
        if len(dupe_ids_group) > 1:
            dupe_hosts_group = payload.find_by_ids(ids=dupe_ids_group)
            if original_id in in_cluster_originals:
                hosts.extend(dupe_hosts_group)
            else:
                hosts_candidates_violations.extend(dupe_hosts_group)

    candidate_violations = (
        [_Violation(type=_ViolationType.DUPLICATE_CANDIDATE, hosts=hosts_candidates_violations)]
        if hosts_candidates_violations
        else []
    )
    in_cluster_violations = [_Violation(type=_ViolationType.DUPLICATE, hosts=hosts)] if hosts else []

    return candidate_violations + in_cluster_violations


def _find_host_cluster_violations(payload: HostCandidateDTO) -> list[_Violation]:
    violations: dict[_ViolationType, list[HostAddInfo]] = defaultdict(list)
    for host in payload.candidates:
        if host.cluster_id is not None:
            if host.cluster_id != payload.cluster_id:
                violations[_ViolationType.FOREIGN_CLUSTER].append(host)
            else:
                violations[_ViolationType.ALREADY_BOUND].append(host)

    return [_Violation(type=type_, hosts=hosts) for type_, hosts in violations.items()]


def _find_host_names_violations(payload: HostCandidateDTO) -> list[_Violation]:
    in_cluster_names = {host.name for host in payload.in_cluster}

    hosts = []
    for host in payload.candidates:
        if host.name in in_cluster_names:
            hosts.append(host)

    if hosts:
        return [_Violation(type=_ViolationType.NAME, hosts=hosts)]

    return []
