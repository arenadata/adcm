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

from typing import Collection

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HOST_PERM,
    VIEW_PROVIDER_PERM,
    ChangeMMPermissions,
    check_config_perm,
    check_custom_perm,
    get_object_for_user,
)
from audit.alt.api import audit_update
from audit.alt.hooks import adjust_denied_on_404_result, extract_current_from_response, extract_previous_from_object
from audit.utils import audit
from cm.api import delete_host, remove_host_from_cluster
from cm.errors import AdcmEx
from cm.models import Cluster, ConcernType, GroupConfig, Host, HostProvider
from cm.services.cluster import perform_host_to_cluster_map
from cm.services.status import notify
from core.cluster.errors import (
    HostAlreadyBoundError,
    HostBelongsToAnotherClusterError,
    HostDoesNotExistError,
)
from django.db.transaction import atomic
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.host.filters import HostClusterFilter, HostFilter
from api_v2.host.permissions import (
    GroupConfigHostsPermissions,
    HostsClusterPermissions,
    HostsPermissions,
)
from api_v2.host.serializers import (
    ClusterHostStatusSerializer,
    HostAddSerializer,
    HostChangeMaintenanceModeSerializer,
    HostCreateSerializer,
    HostGroupConfigSerializer,
    HostSerializer,
    HostUpdateSerializer,
)
from api_v2.host.utils import create_host, maintenance_mode, process_config_issues_policies_hc
from api_v2.utils.audit import (
    host_from_lookup,
    nested_host_does_exist,
    parent_cluster_from_lookup,
    set_add_hosts_name,
    set_removed_host_name,
)
from api_v2.views import ADCMGenericViewSet, ObjectWithStatusViewMixin


@extend_schema_view(
    list=extend_schema(
        operation_id="getHosts",
        description="Get a list of all hosts.",
        summary="GET hosts",
        parameters=[
            OpenApiParameter(name="name", description="Case insensitive and partial filter by host name."),
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=("name", "-name", "id", "-id"),
                default="name",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer(many=True),
        },
    ),
    create=extend_schema(
        operation_id="postHosts",
        description="Create a new hosts.",
        summary="POST hosts",
        responses={
            HTTP_201_CREATED: HostSerializer,
            **{err_code: ErrorSerializer for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getHost",
        description="Get information about a specific host.",
        summary="GET host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    ),
    destroy=extend_schema(
        operation_id="deleteHost",
        description="Delete host from ADCM.",
        summary="DELETE host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_204_NO_CONTENT: None,
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)},
        },
    ),
    partial_update=extend_schema(
        operation_id="patchHost",
        description="Change host Information.",
        summary="PATCH host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
    maintenance_mode=extend_schema(
        operation_id="postHostMaintenanceMode",
        description="Turn on/off maintenance mode on the host.",
        summary="POST host maintenance-mode",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostChangeMaintenanceModeSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
)
class HostViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    ObjectWithStatusViewMixin,
    RetrieveModelMixin,
    ListModelMixin,
    ADCMGenericViewSet,
):
    queryset = (
        Host.objects.select_related("provider", "cluster", "cluster__prototype", "prototype")
        .prefetch_related("concerns", "hostcomponent_set__component__prototype")
        .order_by("fqdn")
    )
    permission_required = [VIEW_HOST_PERM]
    permission_classes = [HostsPermissions]
    filterset_class = HostFilter
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.action == "create":
            return HostCreateSerializer
        elif self.action in ("update", "partial_update"):
            return HostUpdateSerializer
        elif self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        return HostSerializer

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_hostprovider = get_object_for_user(
            user=request.user,
            perms=VIEW_PROVIDER_PERM,
            klass=HostProvider,
            id=serializer.validated_data["hostprovider_id"],
        )

        request_cluster = None
        if serializer.validated_data.get("cluster_id"):
            request_cluster = get_object_for_user(
                user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=serializer.validated_data["cluster_id"]
            )

        with atomic():
            host = create_host(
                provider=request_hostprovider, fqdn=serializer.validated_data["fqdn"], cluster=request_cluster
            )
            process_config_issues_policies_hc(host=host)

        return Response(
            data=HostSerializer(instance=host, context=self.get_serializer_context()).data, status=HTTP_201_CREATED
        )

    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host = self.get_object()
        check_custom_perm(request.user, "remove", "host", host)
        delete_host(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    def partial_update(self, request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        check_custom_perm(request.user, "change", "host", instance)

        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        if valid.get("fqdn") and instance.concerns.filter(type=ConcernType.LOCK).exists():
            raise AdcmEx(code="HOST_CONFLICT", msg="Name change is available only if no locking concern exists")

        if (
            valid.get("fqdn")
            and valid.get("fqdn") != instance.fqdn
            and (instance.cluster or instance.state != "created")
        ):
            raise AdcmEx(code="HOST_UPDATE_ERROR")

        serializer.save()

        return Response(
            status=HTTP_200_OK, data=HostSerializer(instance=instance, context=self.get_serializer_context()).data
        )

    @audit
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        return maintenance_mode(request=request, host=self.get_object())


@extend_schema_view(
    list=extend_schema(
        operation_id="getClusterHosts",
        description="Get a list of all cluster hosts.",
        summary="GET cluster hosts",
        parameters=[
            OpenApiParameter(name="name", description="Case insensitive and partial filter by host name."),
            OpenApiParameter(name="componentId", description="Id of component."),
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=("name", "-name", "id", "-id"),
                default="name",
            ),
            OpenApiParameter(name="search", exclude=True),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postCusterHosts",
        description="Add a new hosts to cluster.",
        summary="POST cluster hosts",
        request=HostAddSerializer(many=True),
        responses={
            HTTP_201_CREATED: HostSerializer(many=True),
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
    retrieve=extend_schema(
        operation_id="getClusterHost",
        description="Get information about a specific cluster host.",
        summary="GET cluster host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    ),
    destroy=extend_schema(
        operation_id="deleteClusterHost",
        description="Unlink host from cluster.",
        summary="DELETE cluster host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_204_NO_CONTENT: None,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
            HTTP_409_CONFLICT: ErrorSerializer,
        },
    ),
    maintenance_mode=extend_schema(
        operation_id="postClusterHostMaintenanceMode",
        description="Turn on/off maintenance mode on the cluster host.",
        summary="POST cluster host maintenance-mode",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostChangeMaintenanceModeSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
    statuses=extend_schema(
        operation_id="getHostStatuses",
        description="Get information about cluster host status.",
        summary="GET host status",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: ClusterHostStatusSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    ),
)
class HostClusterViewSet(
    PermissionListMixin, RetrieveModelMixin, ListModelMixin, ObjectWithStatusViewMixin, ADCMGenericViewSet
):
    permission_required = [VIEW_HOST_PERM]
    permission_classes = [HostsClusterPermissions]
    # have to define it here for `ObjectWithStatusViewMixin` to be able to determine model related to view
    # don't use it directly, use `get_queryset`
    queryset = (
        Host.objects.select_related("cluster", "cluster__prototype", "provider", "prototype")
        .prefetch_related("concerns", "hostcomponent_set__component__prototype")
        .order_by("fqdn")
    )
    filterset_class = HostClusterFilter
    audit_model_hint = Host
    retrieve_status_map_actions = ("list", "statuses")

    def get_serializer_class(self):
        if self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        if self.action == "create":
            return HostAddSerializer

        return HostSerializer

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=self.kwargs["cluster_pk"]
        )

        by_cluster_qs = (
            get_objects_for_user(**self.get_get_objects_for_user_kwargs(self.queryset))
            .filter(cluster=cluster)
            .order_by("fqdn")
        )

        if self.action == "statuses":
            return by_cluster_qs.prefetch_related("hostcomponent_set__component__prototype")

        return by_cluster_qs

    @audit_update(name="Hosts added", object_=parent_cluster_from_lookup).attach_hooks(pre_call=set_add_hosts_name)
    def create(self, request, *_, **kwargs):
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_pk"]
        )
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        check_custom_perm(request.user, "map_host_to", "cluster", cluster)

        multiple_hosts = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=multiple_hosts)
        serializer.is_valid(raise_exception=True)

        try:
            added_hosts: Collection[int] = perform_host_to_cluster_map(
                cluster_id=cluster.pk,
                hosts=[
                    entry["host_id"]
                    for entry in (serializer.validated_data if multiple_hosts else [serializer.validated_data])
                ],
                status_service=notify,
            )
        except HostDoesNotExistError:
            raise AdcmEx("BAD_REQUEST", "At least one host does not exist.") from None
        except HostAlreadyBoundError:
            raise AdcmEx("HOST_CONFLICT", "At least one host is already associated with this cluster.") from None
        except HostBelongsToAnotherClusterError:
            raise AdcmEx("FOREIGN_HOST", "At least one host is already linked to another cluster.") from None

        qs_for_added_hosts = self.get_queryset().filter(id__in=added_hosts)

        context = self.get_serializer_context()

        if multiple_hosts:
            return Response(
                status=HTTP_201_CREATED,
                data=HostSerializer(instance=qs_for_added_hosts, many=True, context=context).data,
            )

        return Response(
            status=HTTP_201_CREATED,
            data=HostSerializer(instance=qs_for_added_hosts.first(), context=context).data,
        )

    @(
        audit_update(name="Host removed", object_=parent_cluster_from_lookup).attach_hooks(
            pre_call=set_removed_host_name, on_collect=adjust_denied_on_404_result(objects_exist=nested_host_does_exist)
        )
    )
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        check_custom_perm(request.user, "unmap_host_from", "cluster", cluster)
        remove_host_from_cluster(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit_update(name="Host updated", object_=host_from_lookup).track_changes(
        before=extract_previous_from_object(Host, "maintenance_mode"),
        after=extract_current_from_response("maintenance_mode"),
    )
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        return maintenance_mode(request=request, host=self.get_object())

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        if host.cluster != cluster:
            raise AdcmEx(code="FOREIGN_HOST", msg=f"Host #{host.id} doesn't belong to cluster #{cluster.id}")

        return Response(
            data=ClusterHostStatusSerializer(
                instance=Host.objects.prefetch_related("hostcomponent_set__component__prototype").get(id=host.id),
                context=self.get_serializer_context(),
            ).data
        )


@extend_schema_view(
    list=extend_schema(
        operation_id="getObjectConfigGroupHosts",
        summary="GET object's config-group hosts",
        description="Get a list of hosts added to object's config-group.",
        responses={HTTP_200_OK: HostGroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getObjectConfigGroupHost",
        summary="GET object's config-group host",
        description="Get information about a specific host of object's config-group.",
        responses={HTTP_200_OK: HostGroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    create=extend_schema(
        operation_id="postObjectConfigGroupHosts",
        summary="POST object's config-group host",
        description="Add host to object's config-group.",
        responses={
            HTTP_201_CREATED: HostGroupConfigSerializer,
            HTTP_400_BAD_REQUEST: ErrorSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
            HTTP_409_CONFLICT: ErrorSerializer,
        },
    ),
    destroy=extend_schema(
        operation_id="deleteObjectConfigGroupHosts",
        summary="DELETE host from object's config-group",
        description="Remove host from object's config-group.",
        responses={HTTP_204_NO_CONTENT: None, HTTP_403_FORBIDDEN: ErrorSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
)
class HostGroupConfigViewSet(
    PermissionListMixin, GetParentObjectMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet
):
    queryset = (
        Host.objects.select_related("provider", "cluster")
        .prefetch_related("concerns", "hostcomponent_set")
        .order_by("fqdn")
    )
    permission_classes = [GroupConfigHostsPermissions]
    permission_required = [VIEW_HOST_PERM]
    filterset_class = HostClusterFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None

    def get_serializer_class(self) -> type[HostGroupConfigSerializer | HostAddSerializer]:
        if self.action == "create":
            return HostAddSerializer

        return HostGroupConfigSerializer

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        return self.queryset.filter(group_config__id=self.kwargs["group_config_pk"])

    def get_group_for_change(self) -> GroupConfig:
        config_group = super().get_parent_object()
        if config_group is None or not isinstance(config_group, GroupConfig):
            raise NotFound

        parent_view_perm = f"cm.view_{config_group.object.__class__.__name__.lower()}"
        if not (
            self.request.user.has_perm(perm=parent_view_perm, obj=config_group.object)
            or self.request.user.has_perm(perm=parent_view_perm)
        ):
            raise NotFound

        check_config_perm(
            user=self.request.user,
            action_type="change",
            model=config_group.object.content_type.model,
            obj=config_group.object,
        )

        return config_group

    @audit
    def create(self, request, *_, **__):
        group_config = self.get_group_for_change()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        host_id = serializer.validated_data["host_id"]
        group_config.check_host_candidate(host_ids=[host_id])
        host = Host.objects.get(pk=host_id)
        group_config.hosts.add(host)

        return Response(status=HTTP_201_CREATED, data=HostGroupConfigSerializer(instance=host).data)

    @audit
    def destroy(self, request, *_, **kwargs):  # noqa: ARG002
        group_config = self.get_group_for_change()

        host = group_config.hosts.filter(pk=kwargs["pk"]).first()
        if not host:
            raise NotFound

        group_config.hosts.remove(host)
        return Response(status=HTTP_204_NO_CONTENT)
