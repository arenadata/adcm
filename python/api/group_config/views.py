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
from cm.models import ConfigLog, GroupConfig, Host, ObjectConfig
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
from rest_framework_extensions.mixins import NestedViewSetMixin

from api.base_view import GenericUIViewSet
from api.group_config.serializers import (
    GroupConfigConfigLogSerializer,
    GroupConfigConfigSerializer,
    GroupConfigHostCandidateSerializer,
    GroupConfigHostSerializer,
    GroupConfigSerializer,
    UIGroupConfigConfigLogSerializer,
    revert_model_name,
)


class GroupConfigFilterSet(FilterSet):
    object_type = CharFilter(field_name="object_type", label="object_type", method="filter_object_type")

    @staticmethod
    def filter_object_type(queryset, name, value):
        value = revert_model_name(value)
        object_type = ContentType.objects.get(app_label="cm", model=value)
        return queryset.filter(**{name: object_type})

    class Meta:
        model = GroupConfig
        fields = ("object_id", "object_type")


class GroupConfigHostViewSet(
    PermissionListMixin,
    NestedViewSetMixin,
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    queryset = Host.objects.all()
    serializer_class = GroupConfigHostSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_host"]
    lookup_url_kwarg = "host_id"
    schema = AutoSchema()
    ordering = ["id"]

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            group_config = GroupConfig.obj.get(id=self.kwargs.get("parent_lookup_group_config"))
            host = serializer.validated_data["id"]
            group_config.check_host_candidate(host_ids=[host.pk])
            group_config.hosts.add(host)
            serializer = self.get_serializer(instance=host)

            return Response(data=serializer.data, status=HTTP_201_CREATED)
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        group_config = GroupConfig.obj.get(id=self.kwargs.get("parent_lookup_group_config"))
        host = self.get_object()
        group_config.hosts.remove(host)

        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        group_config_id = self.kwargs.get("parent_lookup_group_config")
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            context.update({"group_config": group_config})

        return context


class GroupConfigHostCandidateViewSet(
    PermissionListMixin,
    NestedViewSetMixin,
    ReadOnlyModelViewSet,
):
    serializer_class = GroupConfigHostCandidateSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    lookup_url_kwarg = "host_id"
    permission_required = ["cm.view_host"]
    schema = AutoSchema()

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        group_config_id = self.kwargs.get("parent_lookup_group_config")
        if group_config_id is None:
            return Host.objects.none()

        group_config = GroupConfig.obj.get(id=group_config_id)

        return group_config.host_candidate()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        group_config_id = self.kwargs.get("parent_lookup_group_config")
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            context.update({"group_config": group_config})

        return context


class GroupConfigConfigViewSet(
    PermissionListMixin,
    NestedViewSetMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = ObjectConfig.objects.all()
    serializer_class = GroupConfigConfigSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_objectconfig"]
    schema = AutoSchema()
    ordering = ["id"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        group_config_id = self.kwargs.get("parent_lookup_group_config")
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            context.update({"group_config": group_config})
            context.update({"obj_ref__group_config": group_config})

        obj_ref_id = self.kwargs.get("pk")
        if obj_ref_id is not None:
            obj_ref = ObjectConfig.obj.get(id=obj_ref_id)
            context.update({"obj_ref": obj_ref})

        return context


class GroupConfigConfigLogViewSet(
    PermissionListMixin,
    NestedViewSetMixin,
    RetrieveModelMixin,
    ListModelMixin,
    CreateModelMixin,
    GenericUIViewSet,
):
    serializer_class = GroupConfigConfigLogSerializer
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["view_configlog"]
    filterset_fields = ("id",)
    ordering_fields = ("id",)

    def get_serializer_class(self):
        if self.is_for_ui():
            return UIGroupConfigConfigLogSerializer
        return super().get_serializer_class()

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        kwargs = {
            "obj_ref__group_config": self.kwargs.get("parent_lookup_obj_ref__group_config"),
            "obj_ref": self.kwargs.get("parent_lookup_obj_ref"),
        }
        return ConfigLog.objects.filter(**kwargs).order_by("-id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(context["view"], "response"):
            return context

        group_config_id = self.kwargs.get("parent_lookup_obj_ref__group_config")
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            context.update({"obj_ref__group_config": group_config})

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


class GroupConfigViewSet(PermissionListMixin, NestedViewSetMixin, ModelViewSet):
    queryset = GroupConfig.objects.all()
    serializer_class = GroupConfigSerializer
    filterset_class = GroupConfigFilterSet
    permission_classes = (DjangoObjectPermissionsAudit,)
    permission_required = ["cm.view_groupconfig"]
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
            group_config = self.get_object()
            context.update({"group_config": group_config})

        return context
