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

from adcm.permissions import DjangoObjectPermissionsAudit, check_config_perm
from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import ConfigHostGroup, ConfigLog, Host, ObjectConfig
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import CharFilter, FilterSet
from guardian.mixins import PermissionListMixin
from rbac.models import re_apply_object_policy
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

from api.base_view import GenericUIViewSet
from api.config_host_group.serializers import (
    CHGConfigLogSerializer,
    CHGConfigSerializer,
    CHGHostCandidateSerializer,
    CHGHostSerializer,
    CHGSerializer,
    UICHGConfigLogSerializer,
)


class CHGFilterSet(FilterSet):
    object_type = CharFilter(field_name="object_type", label="object_type", method="filter_object_type")

    @staticmethod
    def filter_object_type(queryset, name, value):
        object_type = ContentType.objects.get(app_label="cm", model=value)
        return queryset.filter(**{name: object_type})

    class Meta:
        model = ConfigHostGroup
        fields = ("object_id", "object_type")


class CHGHostViewSet(
    PermissionListMixin,
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = CHGHostSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_host"]
    lookup_url_kwarg = "host_id"
    schema = AutoSchema()
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        host_group_id = self.kwargs.get("parent_lookup_group_config")

        if host_group_id is None:
            return Host.objects.none()

        return Host.objects.filter(config_host_group=host_group_id)

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            host_group = ConfigHostGroup.obj.get(id=self.kwargs.get("parent_lookup_group_config"))
            host = serializer.validated_data["id"]
            host_group.check_host_candidate(host_ids=[host.pk])
            host_group.hosts.add(host)
            serializer = self.get_serializer(instance=host)

            return Response(data=serializer.data, status=HTTP_201_CREATED)
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host_group = ConfigHostGroup.obj.get(id=self.kwargs.get("parent_lookup_group_config"))
        host = self.get_object()
        host_group.hosts.remove(host)

        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        host_group_id = self.kwargs.get("parent_lookup_group_config")
        if host_group_id is not None:
            host_group = ConfigHostGroup.obj.get(id=host_group_id)
            context.update({"group_config": host_group})

        return context


class CHGHostCandidateViewSet(
    PermissionListMixin,
    ReadOnlyModelViewSet,
):
    serializer_class = CHGHostCandidateSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    lookup_url_kwarg = "host_id"
    permission_required = ["cm.view_host"]
    schema = AutoSchema()

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        host_group_id = self.kwargs.get("parent_lookup_group_config")
        if host_group_id is None:
            return Host.objects.none()

        host_group = ConfigHostGroup.obj.get(id=host_group_id)

        return host_group.host_candidate()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        host_group_id = self.kwargs.get("parent_lookup_group_config")
        if host_group_id is not None:
            host_group = ConfigHostGroup.obj.get(id=host_group_id)
            context.update({"group_config": host_group})

        return context


class CHGConfigViewSet(
    PermissionListMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = CHGConfigSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_objectconfig"]
    schema = AutoSchema()
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        host_group_id = self.kwargs.get("parent_lookup_group_config")

        if host_group_id is None:
            return ObjectConfig.objects.none()

        return ObjectConfig.objects.filter(config_host_group=host_group_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        host_group_id = self.kwargs.get("parent_lookup_group_config")
        if host_group_id is not None:
            host_group = ConfigHostGroup.obj.get(id=host_group_id)
            context.update({"group_config": host_group})
            context.update({"obj_ref__group_config": host_group})

        obj_ref_id = self.kwargs.get("pk")
        if obj_ref_id is not None:
            obj_ref = ObjectConfig.obj.get(id=obj_ref_id)
            context.update({"obj_ref": obj_ref})

        return context


class CHGConfigLogViewSet(
    PermissionListMixin,
    RetrieveModelMixin,
    ListModelMixin,
    CreateModelMixin,
    GenericUIViewSet,
):
    serializer_class = CHGConfigLogSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_configlog"]
    filterset_fields = ("id",)
    ordering_fields = ("id",)

    def get_serializer_class(self):
        if self.is_for_ui():
            return UICHGConfigLogSerializer
        return super().get_serializer_class()

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        kwargs = {
            "obj_ref__config_host_group": self.kwargs.get("parent_lookup_obj_ref__group_config"),
            "obj_ref": self.kwargs.get("parent_lookup_obj_ref"),
        }
        return ConfigLog.objects.filter(**kwargs).order_by("-id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        host_group_id = self.kwargs.get("parent_lookup_obj_ref__group_config")
        if host_group_id is not None:
            host_group = ConfigHostGroup.obj.get(id=host_group_id)
            context.update({"obj_ref__group_config": host_group})

        obj_ref_id = self.kwargs.get("parent_lookup_obj_ref")
        if obj_ref_id is not None:
            obj_ref = ObjectConfig.obj.get(id=obj_ref_id)
            context.update({"obj_ref": obj_ref})

        context["ui"] = self.is_for_ui()

        return context

    @audit
    def create(self, request, *args, **kwargs):
        obj = self.get_serializer_context()["obj_ref"].object
        model = type(obj).__name__.lower()
        check_config_perm(user=self.request.user, action_type="change", model=model, obj=obj)
        return super().create(request, *args, **kwargs)


class CHGViewSet(PermissionListMixin, ModelViewSet):
    queryset = ConfigHostGroup.objects.all()
    serializer_class = CHGSerializer
    filterset_class = CHGFilterSet
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["cm.view_confighostgroup"]
    schema = AutoSchema()
    ordering = ["id"]

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            raise AdcmEx("GROUP_CONFIG_DATA_ERROR") from e

        model = serializer.validated_data["object_type"].model_class()
        obj = model.obj.get(id=serializer.validated_data["object_id"])
        model = type(obj).__name__.lower()
        check_config_perm(user=self.request.user, action_type="change", model=model, obj=obj)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        re_apply_object_policy(apply_object=obj)

        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)

    @audit
    def update(self, request, *args, **kwargs):  # noqa: ARG002
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        model = type(instance.object).__name__.lower()
        check_config_perm(user=self.request.user, action_type="change", model=model, obj=instance.object)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        model = type(instance.object).__name__.lower()
        check_config_perm(user=self.request.user, action_type="change", model=model, obj=instance.object)
        self.perform_destroy(instance)

        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        if self.kwargs:
            host_group = self.get_object()
            context.update({"group_config": host_group})

        return context
