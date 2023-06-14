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

from cm.models import Cluster, ClusterObject, GroupConfig, ServiceComponent


class GetParentObjectMixin:
    def get_parent_object(self) -> GroupConfig | Cluster | ClusterObject | ServiceComponent | None:
        parent_object = None

        if "config_group_pk" in self.kwargs:
            parent_object = GroupConfig.objects.get(id=self.kwargs["config_group_pk"])

        elif all(lookup in self.kwargs for lookup in ("servicecomponent_pk", "service_pk", "cluster_pk")) or all(
            lookup in self.kwargs for lookup in ("component_pk", "service_pk", "cluster_pk")
        ):
            parent_object = ServiceComponent.objects.get(
                pk=self.kwargs.get("servicecomponent_pk") or self.kwargs.get("component_pk"),
                cluster=Cluster.objects.get(pk=self.kwargs["cluster_pk"]),
                service=ClusterObject.objects.get(pk=self.kwargs["service_pk"]),
            )

        elif "cluster_pk" in self.kwargs and "service_pk" in self.kwargs:
            cluster = Cluster.objects.get(id=self.kwargs["cluster_pk"])
            parent_object = ClusterObject.objects.get(id=self.kwargs["service_pk"], cluster=cluster)

        elif "cluster_pk" in self.kwargs:
            parent_object = Cluster.objects.get(id=self.kwargs["cluster_pk"])

        return parent_object
