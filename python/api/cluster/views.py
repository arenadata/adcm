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

from itertools import chain

from guardian.mixins import PermissionListMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.cluster.serializers import (
    BindSerializer,
    ClusterBindSerializer,
    ClusterDetailSerializer,
    ClusterDetailUISerializer,
    ClusterSerializer,
    ClusterStatusSerializer,
    ClusterUISerializer,
    ClusterUpdateSerializer,
    DoBindSerializer,
    DoClusterUpgradeSerializer,
    HostComponentSaveSerializer,
    HostComponentSerializer,
    HostComponentUISerializer,
    PostImportSerializer,
)
from api.serializers import ClusterUpgradeSerializer
from api.stack.serializers import (
    BundleServiceUIPrototypeSerializer,
    ImportSerializer,
    ServicePrototypeSerializer,
)
from api.utils import (
    AdcmOrderingFilter,
    check_custom_perm,
    check_obj,
    create,
    get_object_for_user,
    update,
)
from audit.utils import audit
from cm.api import delete_cluster, get_import, unbind
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues
from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    HostComponent,
    Prototype,
    Upgrade,
)
from cm.status_api import make_ui_cluster_status
from cm.upgrade import do_upgrade, get_upgrade
from rbac.viewsets import DjangoOnlyObjectPermissions

VIEW_CLUSTER_PERM = "cm.view_cluster"


def get_obj_conf(cluster_id, service_id):
    cluster = check_obj(Cluster, cluster_id)
    if service_id:
        co = check_obj(ClusterObject, {"cluster": cluster, "id": service_id})
        obj = co
    else:
        obj = cluster

    if not obj:
        raise AdcmEx("CONFIG_NOT_FOUND", "this object has no config")
    if not obj.config:
        raise AdcmEx("CONFIG_NOT_FOUND", "this object has no config")

    return obj


class ClusterList(PermissionListMixin, PaginatedView):
    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer
    serializer_class_ui = ClusterUISerializer
    serializer_class_post = ClusterDetailSerializer
    filterset_fields = ("name", "prototype_id")
    ordering_fields = ("name", "state", "prototype__display_name", "prototype__version_order")
    permission_required = [VIEW_CLUSTER_PERM]

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        return create(serializer)


class ClusterDetail(PermissionListMixin, DetailView):
    queryset = Cluster.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = [VIEW_CLUSTER_PERM]
    serializer_class = ClusterDetailSerializer
    serializer_class_put = ClusterUpdateSerializer
    serializer_class_patch = ClusterUpdateSerializer
    serializer_class_ui = ClusterDetailUISerializer
    lookup_field = "id"
    lookup_url_kwarg = "cluster_id"
    error_code = "CLUSTER_NOT_FOUND"

    @audit
    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=True)

        return update(serializer)

    @audit
    def put(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=False)

        return update(serializer)

    @audit
    def delete(self, request, *args, **kwargs):
        cluster = self.get_object()
        delete_cluster(cluster)

        return Response(status=HTTP_204_NO_CONTENT)


class ClusterBundle(GenericUIView):
    queryset = Prototype.objects.filter(type="service")
    serializer_class = ServicePrototypeSerializer
    serializer_class_ui = BundleServiceUIPrototypeSerializer

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "add_service_to", "cluster", cluster)
        bundle = self.get_queryset().filter(bundle=cluster.prototype.bundle)
        shared = self.get_queryset().filter(shared=True).exclude(bundle=cluster.prototype.bundle)
        serializer = self.get_serializer(
            list(chain(bundle, shared)), many=True, context={"request": request, "cluster": cluster}
        )

        return Response(serializer.data)


class ClusterImport(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    serializer_class_post = PostImportSerializer
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get(request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "view_import_of", "cluster", cluster, "view_clusterbind")
        res = get_import(cluster)

        return Response(res)

    @audit
    def post(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "change_import_of", "cluster", cluster)
        serializer = self.get_serializer(data=request.data, context={"request": request, "cluster": cluster})
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)

            return Response(res, HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ClusterBindList(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = ClusterBindSerializer
    serializer_class_post = DoBindSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "view_import_of", "cluster", cluster, "view_clusterbind")
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer(obj, many=True)

        return Response(serializer.data)

    @audit
    def post(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "change_import_of", "cluster", cluster)
        serializer = self.get_serializer(data=request.data)

        return create(serializer, cluster=cluster)


class ClusterBindDetail(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get_obj(kwargs, bind_id):
        bind = ClusterBind.objects.filter(pk=bind_id).first()
        if bind:
            return bind.source_service

        return None

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        bind = check_obj(ClusterBind, {"cluster": cluster, "id": kwargs["bind_id"]})
        check_custom_perm(request.user, "view_import_of", "cluster", cluster, "view_clusterbind")
        serializer = self.get_serializer(bind)

        return Response(serializer.data)

    @audit
    def delete(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        bind = check_obj(ClusterBind, {"cluster": cluster, "id": kwargs["bind_id"]})
        check_custom_perm(request.user, "change_import_of", "cluster", cluster)
        unbind(bind)

        return Response(status=HTTP_204_NO_CONTENT)


class ClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ClusterUpgradeSerializer
    permission_classes = (IsAuthenticated,)

    def get_ordering(self):
        order = AdcmOrderingFilter()
        return order.get_ordering(self.request, self.get_queryset(), self)

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "view_upgrade_of", "cluster", cluster)
        update_hierarchy_issues(cluster)
        obj = get_upgrade(cluster, self.get_ordering())
        serializer = self.serializer_class(obj, many=True, context={"cluster_id": cluster.id, "request": request})

        return Response(serializer.data)


class ClusterUpgradeDetail(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ClusterUpgradeSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "view_upgrade_of", "cluster", cluster)
        obj = check_obj(Upgrade, {"id": kwargs["upgrade_id"], "bundle__name": cluster.prototype.bundle.name})
        serializer = self.serializer_class(obj, context={"cluster_id": cluster.id, "request": request})

        return Response(serializer.data)


class DoClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = DoClusterUpgradeSerializer
    permission_classes = (IsAuthenticated,)

    @audit
    def post(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "do_upgrade_of", "cluster", cluster)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        upgrade = check_obj(
            Upgrade,
            kwargs.get("upgrade_id"),
            "UPGRADE_NOT_FOUND",
        )
        config = serializer.validated_data.get("config", {})
        attr = serializer.validated_data.get("attr", {})
        hc = serializer.validated_data.get("hc", [])

        return Response(
            data=do_upgrade(cluster, upgrade, config, attr, hc),
            status=HTTP_201_CREATED,
        )


class StatusList(GenericUIView):
    permission_classes = (IsAuthenticated,)
    queryset = HostComponent.objects.all()
    serializer_class = ClusterStatusSerializer

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        host_components = self.get_queryset().filter(cluster=cluster)
        if self._is_for_ui():
            return Response(make_ui_cluster_status(cluster, host_components))
        else:
            serializer = self.get_serializer(host_components, many=True)

            return Response(serializer.data)


class HostComponentList(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = HostComponentSerializer
    serializer_class_ui = HostComponentUISerializer
    serializer_class_post = HostComponentSaveSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "view_host_components_of", "cluster", cluster, "view_hostcomponent")
        hc = self.get_queryset().prefetch_related("service", "component", "host").filter(cluster=cluster)
        if self._is_for_ui():
            ui_hc = HostComponent()
            ui_hc.hc = hc
            serializer = self.get_serializer(ui_hc, context={"request": request, "cluster": cluster})
        else:
            serializer = self.get_serializer(hc, many=True)

        return Response(serializer.data)

    @audit
    def post(self, request, *args, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_id"])
        check_custom_perm(request.user, "edit_host_components_of", "cluster", cluster)
        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request,
                "cluster": cluster,
            },
        )
        if serializer.is_valid():
            hc_list = serializer.save()
            response_serializer = self.serializer_class(hc_list, many=True, context={"request": request})

            return Response(response_serializer.data, HTTP_201_CREATED)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class HostComponentDetail(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = HostComponentSerializer
    permission_classes = (IsAuthenticated,)

    def get_obj(self, cluster_id, hs_id):
        cluster = get_object_for_user(self.request.user, VIEW_CLUSTER_PERM, Cluster, id=cluster_id)
        check_custom_perm(self.request.user, "view_host_components_of", "cluster", cluster, "view_hostcomponent")

        return check_obj(HostComponent, {"id": hs_id, "cluster": cluster}, "HOSTSERVICE_NOT_FOUND")

    def get(self, request, *args, **kwargs):
        obj = self.get_obj(kwargs["cluster_id"], kwargs["hs_id"])
        serializer = self.get_serializer(obj)

        return Response(serializer.data)
