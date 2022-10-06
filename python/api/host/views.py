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

from django_filters import rest_framework as drf_filters
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.host.serializers import (
    ClusterHostSerializer,
    HostDetailSerializer,
    HostDetailUISerializer,
    HostSerializer,
    HostUISerializer,
    HostUpdateSerializer,
    ProvideHostSerializer,
    StatusSerializer,
)
from api.utils import check_custom_perm, create, get_object_for_user
from audit.utils import audit
from cm.api import (
    add_host_to_cluster,
    delete_host,
    load_service_map,
    remove_host_from_cluster,
)
from cm.errors import AdcmEx
from cm.models import (
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    ServiceComponent,
)
from cm.status_api import make_ui_host_status
from rbac.viewsets import DjangoOnlyObjectPermissions

CLUSTER_VIEW = "cm.view_cluster"
PROVIDER_VIEW = "cm.view_hostprovider"
HOST_VIEW = "cm.view_host"


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class HostFilter(drf_filters.FilterSet):
    cluster_is_null = drf_filters.BooleanFilter(field_name="cluster_id", lookup_expr="isnull")
    provider_is_null = drf_filters.BooleanFilter(field_name="provider_id", lookup_expr="isnull")
    group_config = drf_filters.ModelChoiceFilter(
        queryset=GroupConfig.objects.all(), field_name="group_config", label="GroupConfig"
    )
    hostcomponent__service_id = drf_filters.ModelChoiceFilter(
        queryset=ClusterObject.objects.all(),
        field_name="hostcomponent__service_id",
        label="HostComponentService",
        distinct=True,
    )
    hostcomponent__component_id = drf_filters.ModelChoiceFilter(
        queryset=ServiceComponent.objects.all(),
        field_name="hostcomponent__component_id",
        label="HostComponentComponent",
        distinct=True,
    )

    exclude_group_config__in = NumberInFilter(
        field_name="group_config", lookup_expr="in", label="ExcludeGroupConfigIn", exclude=True
    )

    class Meta:
        model = Host
        fields = [
            "cluster_id",
            "prototype_id",
            "provider_id",
            "fqdn",
            "cluster_is_null",
            "provider_is_null",
            "group_config",
            "hostcomponent__service_id",
            "hostcomponent__component_id",
            "exclude_group_config__in",
        ]


def get_host_queryset(queryset, user, kwargs):
    if "cluster_id" in kwargs:
        cluster = get_object_for_user(user, CLUSTER_VIEW, Cluster, id=kwargs["cluster_id"])
        queryset = queryset.filter(cluster=cluster)
    if "provider_id" in kwargs:
        provider = get_object_for_user(user, PROVIDER_VIEW, HostProvider, id=kwargs["provider_id"])
        queryset = queryset.filter(provider=provider)

    return queryset


class HostList(PermissionListMixin, PaginatedView):
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    serializer_class_ui = HostUISerializer
    permission_required = [HOST_VIEW]
    filterset_class = HostFilter
    filterset_fields = (
        "cluster_id",
        "prototype_id",
        "provider_id",
        "fqdn",
        "cluster_is_null",
        "provider_is_null",
        "group_config",
        "hostcomponent__service_id",
        "hostcomponent__component_id",
        "exclude_group_config__in",
    )
    ordering_fields = (
        "fqdn",
        "state",
        "provider__name",
        "cluster__name",
        "prototype__display_name",
        "prototype__version_order",
    )

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        queryset = get_host_queryset(queryset, self.request.user, self.kwargs)

        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(queryset))

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={
                "request": request,
                "cluster_id": kwargs.get("cluster_id", None),
                "provider_id": kwargs.get("provider_id", None),
            },
        )
        if serializer.is_valid():
            if "provider_id" in kwargs:  # List provider hosts
                provider = get_object_for_user(
                    request.user, PROVIDER_VIEW, HostProvider, id=kwargs["provider_id"]
                )
            else:
                provider = serializer.validated_data.get("provider_id")
                provider = get_object_for_user(
                    request.user, PROVIDER_VIEW, HostProvider, id=provider.id
                )

            check_custom_perm(request.user, "add_host_to", "hostprovider", provider)

            return create(serializer)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class HostListProvider(HostList):
    serializer_class = ProvideHostSerializer


class HostListCluster(HostList):
    serializer_class = ClusterHostSerializer

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            validated_data = serializer.validated_data

            cluster = None
            if "cluster_id" in kwargs:
                cluster = get_object_for_user(
                    request.user, CLUSTER_VIEW, Cluster, id=kwargs["cluster_id"]
                )

            host = get_object_for_user(request.user, HOST_VIEW, Host, id=validated_data.get("id"))
            check_custom_perm(request.user, "map_host_to", "cluster", cluster)
            add_host_to_cluster(cluster, host)

            return Response(self.get_serializer(host).data, status=HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


def check_host(host, cluster):
    if host.cluster != cluster:
        msg = f"Host #{host.id} doesn't belong to cluster #{cluster.id}"

        raise AdcmEx("FOREIGN_HOST", msg)


class HostDetail(PermissionListMixin, DetailView):
    queryset = Host.objects.all()
    serializer_class = HostDetailSerializer
    serializer_class_ui = HostDetailUISerializer
    serializer_class_put = HostUpdateSerializer
    serializer_class_patch = HostUpdateSerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = [HOST_VIEW]
    lookup_field = "id"
    lookup_url_kwarg = "host_id"
    error_code = "HOST_NOT_FOUND"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        queryset = get_host_queryset(queryset, self.request.user, self.kwargs)

        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(queryset))

    @audit
    def delete(self, request, *args, **kwargs):
        host = self.get_object()
        if "cluster_id" in kwargs:
            # Remove host from cluster
            cluster = get_object_for_user(
                request.user, CLUSTER_VIEW, Cluster, id=kwargs["cluster_id"]
            )
            check_host(host, cluster)
            check_custom_perm(request.user, "unmap_host_from", "cluster", cluster)
            remove_host_from_cluster(host)
        else:
            # Delete host (and all corresponding host services:components)
            check_custom_perm(request.user, "remove", "host", host)
            delete_host(host)

        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    def patch(self, request, *args, **kwargs):
        return self.__update_host_object(request, *args, **kwargs)

    @audit
    def put(self, request, *args, **kwargs):
        return self.__update_host_object(request, partial=False, *args, **kwargs)

    def __update_host_object(
        self,
        request,
        *args,
        partial=True,
        **kwargs,
    ):
        host = self.get_object()
        check_custom_perm(request.user, "change", "host", host)
        serializer = self.get_serializer(
            host,
            data=request.data,
            context={
                "request": request,
                "prototype_id": kwargs.get("prototype_id", None),
                "cluster_id": kwargs.get("cluster_id", None),
                "provider_id": kwargs.get("provider_id", None),
            },
            partial=partial,
        )

        serializer.is_valid(raise_exception=True)
        if "maintenance_mode" in serializer.validated_data:
            self._check_maintenance_mode_constraint(
                host, serializer.validated_data.get("maintenance_mode")
            )

        if (
            "fqdn" in request.data
            and request.data["fqdn"] != host.fqdn
            and (host.cluster or host.state != "created")
        ):
            raise AdcmEx("HOST_UPDATE_ERROR")

        serializer.save(**kwargs)
        load_service_map()

        return Response(self.get_serializer(self.get_object()).data, status=HTTP_200_OK)

    @staticmethod
    def _check_maintenance_mode_constraint(host: Host, new_mode: bool):
        if host.maintenance_mode == new_mode:
            return
        if not host.is_maintenance_mode_available:
            raise AdcmEx("MAINTENANCE_MODE_NOT_AVAILABLE")


class StatusList(GenericUIView):
    queryset = HostComponent.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = StatusSerializer

    def get(self, request, *args, **kwargs):
        cluster = None
        host = get_object_for_user(request.user, HOST_VIEW, Host, id=kwargs["host_id"])
        if "cluster_id" in kwargs:
            cluster = get_object_for_user(
                request.user, CLUSTER_VIEW, Cluster, id=kwargs["cluster_id"]
            )
        if "provider_id" in kwargs:
            provider = get_object_for_user(
                request.user, PROVIDER_VIEW, HostProvider, id=kwargs["provider_id"]
            )
            host = get_object_for_user(
                request.user,
                HOST_VIEW,
                Host.objects.filter(provider=provider),
                id=kwargs["host_id"],
            )

        if self._is_for_ui():
            host_components = self.get_queryset().filter(host=host)
            if cluster is not None:
                host_components = self.get_queryset().filter(host=host, cluster=cluster)

            return Response(make_ui_host_status(host, host_components))
        else:
            serializer = self.get_serializer(host)

            return Response(serializer.data)
