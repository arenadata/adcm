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

from functools import reduce
from operator import or_
from typing import Iterable

from core.cluster.types import MovedHosts
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, Q

from cm.models import ClusterObject, ServiceComponent


class HostGroupRepoMixin:
    group_hosts_model: Model
    group_hosts_field_name: str

    def remove_unmapped_hosts_from_groups(self, unmapped_hosts: MovedHosts) -> None:
        if not (unmapped_hosts.services or unmapped_hosts.components):
            return

        hosts_in_service_groups, hosts_in_component_groups = Q(), Q()
        object_type = f"{self.group_hosts_field_name}__object_type"
        object_id = f"{self.group_hosts_field_name}__object_id"

        if unmapped_hosts.services:
            hosts_in_service_groups = Q(
                Q(**{object_type: ContentType.objects.get_for_model(ClusterObject)}),
                self._combine_with_or(
                    Q(host_id__in=hosts, **{object_id: service_id})
                    for service_id, hosts in unmapped_hosts.services.items()
                ),
            )

        if unmapped_hosts.components:
            hosts_in_component_groups = Q(
                Q(**{object_type: ContentType.objects.get_for_model(ServiceComponent)}),
                self._combine_with_or(
                    Q(host_id__in=hosts, **{object_id: component_id})
                    for component_id, hosts in unmapped_hosts.components.items()
                ),
            )

        self.group_hosts_model.objects.filter(
            self._combine_with_or(filter(bool, [hosts_in_service_groups, hosts_in_component_groups]))
        ).delete()

    def _combine_with_or(self, clauses: Iterable[Q]) -> Q:
        return reduce(or_, clauses, Q())
