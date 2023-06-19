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

from contextlib import suppress

from cm.models import (
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostProvider,
    ServiceComponent,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import ObjectDoesNotExist


class GetParentObjectMixin:
    def get_parent_object(self) -> GroupConfig | Cluster | ClusterObject | ServiceComponent | Host | None:
        parent_object = None

        with suppress(ObjectDoesNotExist):
            if all(lookup in self.kwargs for lookup in ("component_pk", "service_pk", "cluster_pk")):
                parent_object = ServiceComponent.objects.get(
                    pk=self.kwargs["component_pk"],
                    cluster_id=self.kwargs["cluster_pk"],
                    service_id=self.kwargs["service_pk"],
                )

            elif "cluster_pk" in self.kwargs and "service_pk" in self.kwargs:
                parent_object = ClusterObject.objects.get(
                    pk=self.kwargs["service_pk"], cluster_id=self.kwargs["cluster_pk"]
                )

            elif "cluster_pk" in self.kwargs and "host_pk" in self.kwargs:
                parent_object = Host.objects.get(pk=self.kwargs["host_pk"], cluster_id=self.kwargs["cluster_pk"])

            elif "host_pk" in self.kwargs:
                parent_object = Host.objects.get(pk=self.kwargs["host_pk"])

            elif "cluster_pk" in self.kwargs:
                parent_object = Cluster.objects.get(pk=self.kwargs["cluster_pk"])

            elif "provider_pk" in self.kwargs:
                parent_object = HostProvider.objects.get(pk=self.kwargs["provider_pk"])

            if "config_group_pk" in self.kwargs:
                parent_object = GroupConfig.objects.get(
                    pk=self.kwargs["config_group_pk"],
                    object_id=parent_object.pk,
                    object_type=ContentType.objects.get_for_model(model=parent_object),
                )

        return parent_object
