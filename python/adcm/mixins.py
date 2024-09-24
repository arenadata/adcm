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
from typing import TypeAlias

from cm.models import (
    Cluster,
    GroupConfig,
    Host,
    HostProvider,
    Service,
    ServiceComponent,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import ObjectDoesNotExist

ParentObject: TypeAlias = GroupConfig | Cluster | Service | ServiceComponent | HostProvider | Host | None


class GetParentObjectMixin:
    kwargs: dict

    def get_parent_object(self) -> ParentObject:
        parent_object = None

        with suppress(ObjectDoesNotExist):
            if all(lookup in self.kwargs for lookup in ("component_pk", "service_pk", "cluster_pk")):
                parent_object = ServiceComponent.objects.select_related(
                    "prototype", "cluster__prototype", "service__prototype"
                ).get(
                    pk=self.kwargs["component_pk"],
                    cluster_id=self.kwargs["cluster_pk"],
                    service_id=self.kwargs["service_pk"],
                )

            elif "cluster_pk" in self.kwargs and "service_pk" in self.kwargs:
                parent_object = Service.objects.select_related("prototype", "cluster__prototype").get(
                    pk=self.kwargs["service_pk"], cluster_id=self.kwargs["cluster_pk"]
                )

            elif "cluster_pk" in self.kwargs and "host_pk" in self.kwargs:
                parent_object = Host.objects.select_related(
                    "prototype", "cluster__prototype", "provider__prototype"
                ).get(pk=self.kwargs["host_pk"], cluster_id=self.kwargs["cluster_pk"])

            elif "host_pk" in self.kwargs:
                parent_object = Host.objects.select_related(
                    "prototype", "cluster__prototype", "provider__prototype"
                ).get(pk=self.kwargs["host_pk"])

            elif "cluster_pk" in self.kwargs:
                parent_object = Cluster.objects.select_related("prototype").get(pk=self.kwargs["cluster_pk"])

            elif "hostprovider_pk" in self.kwargs:
                parent_object = HostProvider.objects.select_related("prototype").get(pk=self.kwargs["hostprovider_pk"])

            if "group_config_pk" in self.kwargs and parent_object:
                parent_object = GroupConfig.objects.get(
                    pk=self.kwargs["group_config_pk"],
                    object_id=parent_object.pk,
                    object_type=ContentType.objects.get_for_model(model=parent_object.__class__),
                )

        return parent_object
