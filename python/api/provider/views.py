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

from guardian.mixins import PermissionListMixin
from rest_framework import permissions, status
from rest_framework.response import Response

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.provider.serializers import (
    DoProviderUpgradeSerializer,
    ProviderDetailSerializer,
    ProviderDetailUISerializer,
    ProviderSerializer,
    ProviderUISerializer,
)
from api.serializers import ProviderUpgradeSerializer
from api.utils import (
    AdcmFilterBackend,
    AdcmOrderingFilter,
    check_custom_perm,
    check_obj,
    create,
    get_object_for_user,
)
from audit.utils import audit
from cm.api import delete_host_provider
from cm.issue import update_hierarchy_issues
from cm.models import HostProvider, Upgrade
from cm.upgrade import get_upgrade
from rbac.viewsets import DjangoOnlyObjectPermissions


class ProviderList(PermissionListMixin, PaginatedView):
    """
    get:
    List all host providers

    post:
    Create new host provider
    """

    queryset = HostProvider.objects.all()
    serializer_class = ProviderSerializer
    serializer_class_ui = ProviderUISerializer
    serializer_class_post = ProviderDetailSerializer
    filterset_fields = ("name", "prototype_id")
    ordering_fields = ("id", "name", "state", "prototype__display_name", "prototype__version_order")
    permission_required = ["cm.view_hostprovider"]

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        return create(serializer)


class ProviderDetail(PermissionListMixin, DetailView):
    """
    get:
    Show host provider
    """

    queryset = HostProvider.objects.all()
    serializer_class = ProviderDetailSerializer
    serializer_class_ui = ProviderDetailUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ["cm.view_hostprovider"]
    lookup_field = "id"
    lookup_url_kwarg = "provider_id"
    error_code = "PROVIDER_NOT_FOUND"

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Remove host provider
        """
        provider = self.get_object()
        delete_host_provider(provider)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ProviderUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (AdcmFilterBackend, AdcmOrderingFilter)

    def get_ordering(self):
        order = AdcmOrderingFilter()
        return order.get_ordering(self.request, self.get_queryset(), self)

    def get(self, request, *args, **kwargs):
        """
        List all available upgrades for specified host provider
        """
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_id"])
        check_custom_perm(request.user, "view_upgrade_of", "hostprovider", provider)
        update_hierarchy_issues(provider)
        obj = get_upgrade(provider, self.get_ordering())
        serializer = self.serializer_class(obj, many=True, context={"provider_id": provider.id, "request": request})
        return Response(serializer.data)


class ProviderUpgradeDetail(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ProviderUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        List all available upgrades for specified host provider
        """
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_id"])
        check_custom_perm(request.user, "view_upgrade_of", "hostprovider", provider)
        obj = check_obj(Upgrade, {"id": kwargs["upgrade_id"], "bundle__name": provider.prototype.bundle.name})
        serializer = self.serializer_class(obj, context={"provider_id": provider.id, "request": request})
        return Response(serializer.data)


class DoProviderUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = DoProviderUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @audit
    def post(self, request, *args, **kwargs):
        provider = get_object_for_user(request.user, "cm.view_hostprovider", HostProvider, id=kwargs["provider_id"])
        check_custom_perm(request.user, "do_upgrade_of", "hostprovider", provider)
        serializer = self.get_serializer(data=request.data)

        return create(serializer, upgrade_id=int(kwargs["upgrade_id"]), obj=provider)
