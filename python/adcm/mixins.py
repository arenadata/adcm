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

from typing import TypeAlias, overload

from cm.models import (
    ADCM,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    Provider,
    Service,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import ObjectDoesNotExist

ParentObject: TypeAlias = ConfigHostGroup | Cluster | Service | Component | Provider | Host | ADCM


class GetParentObjectMixin:
    kwargs: dict

    @overload
    def get_parent_object(self, raise_: None) -> ParentObject | None:
        ...

    @overload
    def get_parent_object(self, raise_: Exception) -> ParentObject:
        ...

    @overload
    def get_parent_object(self, raise_: Exception | None = None) -> ParentObject | None:
        ...

    def get_parent_object(self, raise_: Exception | None = None) -> ParentObject | None:
        try:
            return self._get_parent_object_unsafe()
        except ObjectDoesNotExist as e:
            if raise_:
                raise raise_ from e

            return None

    def _get_parent_object_unsafe(self) -> ParentObject:
        if all(lookup in self.kwargs for lookup in ("component_pk", "service_pk", "cluster_pk")):
            parent_object = Component.objects.select_related(
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
            parent_object = Host.objects.select_related("prototype", "cluster__prototype", "provider__prototype").get(
                pk=self.kwargs["host_pk"], cluster_id=self.kwargs["cluster_pk"]
            )

        elif "host_pk" in self.kwargs:
            parent_object = Host.objects.select_related("prototype", "cluster__prototype", "provider__prototype").get(
                pk=self.kwargs["host_pk"]
            )

        elif "cluster_pk" in self.kwargs:
            parent_object = Cluster.objects.select_related("prototype").get(pk=self.kwargs["cluster_pk"])

        elif "provider_pk" in self.kwargs:
            parent_object = Provider.objects.select_related("prototype").get(pk=self.kwargs["provider_pk"])

        if "config_host_group_pk" in self.kwargs and parent_object:
            parent_object = ConfigHostGroup.objects.get(
                pk=self.kwargs["config_host_group_pk"],
                object_id=parent_object.pk,
                object_type=ContentType.objects.get_for_model(model=parent_object.__class__),
            )

        return parent_object
