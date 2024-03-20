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

from cm.models import ObjectType, Prototype
from django.db.models.query import QuerySet
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.viewsets import GenericViewSet

from api_ui.stack.serializers import PrototypeUISerializer


class PrototypeUIViewMixin:
    @staticmethod
    def get_distinct_queryset(queryset: QuerySet) -> QuerySet:
        distinct_prototype_pks = set()
        distinct_prototype_display_names = set()
        for prototype in queryset:
            if prototype.display_name in distinct_prototype_display_names:
                continue

            distinct_prototype_display_names.add(prototype.display_name)
            distinct_prototype_pks.add(prototype.pk)

        return queryset.filter(pk__in=distinct_prototype_pks)


class ClusterPrototypeUIViewSet(PrototypeUIViewMixin, ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = PrototypeUISerializer
    schema = AutoSchema()
    ordering_fields = ("id", "name", "display_name")
    ordering = ["display_name"]

    def get_queryset(self):
        return self.get_distinct_queryset(queryset=Prototype.objects.filter(type=ObjectType.CLUSTER))


class ProviderPrototypeUIViewSet(PrototypeUIViewMixin, ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = PrototypeUISerializer
    schema = AutoSchema()
    ordering_fields = ("id", "name", "display_name")
    ordering = ["display_name"]

    def get_queryset(self):
        return self.get_distinct_queryset(queryset=Prototype.objects.filter(type=ObjectType.PROVIDER))
