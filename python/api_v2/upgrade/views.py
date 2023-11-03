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
from api_v2.action.serializers import ActionRunSerializer
from api_v2.action.utils import get_action_configuration, insert_service_ids
from api_v2.config.utils import convert_adcm_meta_to_attr, represent_string_as_json_type
from api_v2.task.serializers import TaskListSerializer
from api_v2.upgrade.serializers import UpgradeListSerializer, UpgradeRetrieveSerializer
from api_v2.views import CamelCaseGenericViewSet
from cm.errors import AdcmEx
from cm.models import Cluster, HostProvider, PrototypeConfig, TaskLog, Upgrade
from cm.upgrade import check_upgrade, do_upgrade, get_upgrade
from rbac.models import User
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_CLUSTER_UPGRADE_PERM,
    VIEW_PROVIDER_PERM,
    VIEW_PROVIDER_UPGRADE_PERM,
    check_custom_perm,
    get_object_for_user,
)


class UpgradeViewSet(  # pylint: disable=too-many-ancestors
    ListModelMixin,
    GetParentObjectMixin,
    RetrieveModelMixin,
    CamelCaseGenericViewSet,
):
    queryset = (
        Upgrade.objects.select_related("action", "bundle", "action__prototype")
        .prefetch_related("bundle__prototype_set")
        .order_by("pk")
    )
    filter_backends = []

    def get_serializer_class(self) -> type[UpgradeListSerializer | ActionRunSerializer | UpgradeRetrieveSerializer]:
        if self.action == "retrieve":
            return UpgradeRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return UpgradeListSerializer

    def get_object(self):
        parent_object: Cluster | HostProvider | None = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't get parent object for upgrade")

        check_custom_perm(
            user=self.request.user,
            action_type="view_upgrade_of",
            model=parent_object.__class__.__name__.lower(),
            obj=parent_object,
        )

        if self.action == "run":
            check_custom_perm(
                user=self.request.user,
                action_type="do_upgrade_of",
                model=parent_object.__class__.__name__.lower(),
                obj=parent_object,
            )

        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        return obj

    def get_parent_object_for_user(self, user: User) -> Cluster | HostProvider:
        parent: Cluster | HostProvider | None = self.get_parent_object()
        if parent is None or not isinstance(parent, (Cluster, HostProvider)):
            message = "Can't find upgrade's parent object"
            raise NotFound(message)

        if isinstance(parent, Cluster):
            cluster = get_object_for_user(user=user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=parent.pk)
            if not user.has_perm(perm=VIEW_CLUSTER_UPGRADE_PERM, obj=cluster):
                raise PermissionDenied(f"You can't view upgrades of {cluster}")
            return cluster

        if isinstance(parent, HostProvider):
            hostprovider = get_object_for_user(user=user, perms=VIEW_PROVIDER_PERM, klass=HostProvider, id=parent.pk)
            if not user.has_perm(perm=VIEW_PROVIDER_UPGRADE_PERM, obj=hostprovider):
                raise PermissionDenied(f"You can't view upgrades of {hostprovider}")
            return hostprovider

        raise ValueError("Wrong object")

    def get_upgrade(self, parent: Cluster | HostProvider):
        upgrade = self.get_object()
        if upgrade.bundle.name != parent.prototype.bundle.name:
            raise AdcmEx(code="UPGRADE_NOT_FOUND")

        upgrade_is_allowed, error = check_upgrade(obj=parent, upgrade=upgrade)
        if not upgrade_is_allowed:
            raise AdcmEx(code="UPGRADE_NOT_FOUND", msg=error)

        return upgrade

    def list(self, request: Request, *args, **kwargs) -> Response:
        parent: Cluster | HostProvider = self.get_parent_object_for_user(user=request.user)
        upgrades = get_upgrade(obj=parent)
        serializer = self.get_serializer_class()(instance=upgrades, many=True)
        return Response(data=serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        parent: Cluster | HostProvider = self.get_parent_object_for_user(user=request.user)

        upgrade = self.get_upgrade(parent=parent)

        config_schema = None
        config = None
        adcm_meta = None

        if upgrade.action:
            config_schema, config, adcm_meta = get_action_configuration(action_=upgrade.action, object_=parent)

        serializer = self.get_serializer_class()(
            instance=upgrade,
            context={"parent": parent, "config_schema": config_schema, "config": config, "adcm_meta": adcm_meta},
        )

        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def run(self, request: Request, *_, **__) -> Response:
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent: Cluster | HostProvider = self.get_parent_object_for_user(user=request.user)
        upgrade = self.get_upgrade(parent=parent)

        configuration = serializer.validated_data["configuration"]
        config = {}
        adcm_meta = {}

        if configuration is not None:
            config = configuration["config"]
            adcm_meta = configuration["adcm_meta"]

        if upgrade.action:
            prototype_configs = PrototypeConfig.objects.filter(
                prototype=upgrade.action.prototype, type="json", action=upgrade.action
            ).order_by("pk")
            config = represent_string_as_json_type(prototype_configs=prototype_configs, value=config)

        attr = convert_adcm_meta_to_attr(adcm_meta=adcm_meta)

        result = do_upgrade(
            obj=parent,
            upgrade=upgrade,
            config=config,
            attr=attr,
            hostcomponent=insert_service_ids(hc_create_data=serializer.validated_data["host_component_map"]),
        )

        if (task_id := result["task_id"]) is None:
            return Response(status=HTTP_204_NO_CONTENT)

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=TaskLog.objects.get(pk=task_id)).data)
