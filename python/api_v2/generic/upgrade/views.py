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

from adcm.feature_flags import use_new_job_scheduler
from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_CLUSTER_UPGRADE_PERM,
    VIEW_PROVIDER_PERM,
    VIEW_PROVIDER_UPGRADE_PERM,
    check_custom_perm,
    get_object_for_user,
)
from cm.errors import AdcmEx
from cm.legacy.services.bundle_alt.render import ContextGatherer
from cm.legacy.upgrade import check_upgrade, get_upgrade
from cm.models import Bundle, Cluster, ObjectType, Prototype, Provider, TaskLog, Upgrade
from core.legacy.cluster.types import HostComponentEntry
from django.db.models import OuterRef, Prefetch, Subquery
from infra.services import get_config_service, get_job_service, get_wizard_service
from rbac.models import User
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from use_cases.dto import ConfigurationDTO, UpgradeActionDTO
from use_cases.transition.upgrade import upgrade_object
import core

from api_v2.generic.action.serializers import UpgradeRunSerializer
from api_v2.generic.action.utils import get_action_configuration
from api_v2.generic.upgrade.filters import UpgradeFilter
from api_v2.generic.upgrade.serializers import UpgradeListSerializer, UpgradeRetrieveSerializer
from api_v2.task.serializers import TaskListSerializer
from api_v2.utils.checks import check_hostcomponents_objects_exist
from api_v2.utils.config import convert_main_config
from api_v2.views import ADCMGenericViewSet


class UpgradeViewSet(ListModelMixin, GetParentObjectMixin, RetrieveModelMixin, ADCMGenericViewSet):
    queryset = Upgrade.objects.select_related("action", "action__prototype")
    filterset_class = UpgradeFilter
    pagination_class = None

    def handle_exception(self, exc: Exception) -> Response:
        # temporal handling
        if isinstance(exc, core.config.OperationError):
            exc = AdcmEx(code="UPGRADE_OPERATION_ERROR", msg=exc.args[0])

        return super().handle_exception(exc)

    def get_serializer_class(self) -> type[UpgradeListSerializer | UpgradeRunSerializer | UpgradeRetrieveSerializer]:
        if self.action == "retrieve":
            return UpgradeRetrieveSerializer

        if self.action == "run":
            return UpgradeRunSerializer

        return UpgradeListSerializer

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        queryset = super().get_queryset(*args, **kwargs)
        prototype_qs = Prototype.objects.filter(
            bundle=OuterRef("pk"), type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER]
        ).order_by("id")

        bundle_qs = Bundle.objects.annotate(
            display_name=Subquery(prototype_qs.values("display_name")[:1]),
            prototype_id=Subquery(prototype_qs.values("id")[:1]),
            license_statues=Subquery(prototype_qs.values("license")[:1]),
        )

        return queryset.prefetch_related(Prefetch("bundle", queryset=bundle_qs)).order_by("pk")

    def get_object(self):
        parent_object: Cluster | Provider | None = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't get parent object for upgrade")

        check_custom_perm(
            user=self.request.user,
            action_type="view_upgrade_of",
            model=parent_object.__class__.__name__.lower(),
            obj=parent_object,
            second_perm=f"view_upgrade_of_{parent_object.__class__.__name__.lower()}",
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
        return get_object_or_404(queryset, **filter_kwargs)

    def get_parent_object_for_user(self, user: User) -> Cluster | Provider:
        parent: Cluster | Provider | None = self.get_parent_object()
        if parent is None or not isinstance(parent, (Cluster, Provider)):
            message = "Can't find upgrade's parent object"
            raise NotFound(message)

        if isinstance(parent, Cluster):
            cluster = get_object_for_user(user=user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=parent.pk)
            if not user.has_perm(perm=VIEW_CLUSTER_UPGRADE_PERM, obj=cluster) and not user.has_perm(
                perm=VIEW_CLUSTER_UPGRADE_PERM
            ):
                raise PermissionDenied(f"You can't view upgrades of {cluster}")
            return cluster

        if isinstance(parent, Provider):
            provider = get_object_for_user(user=user, perms=VIEW_PROVIDER_PERM, klass=Provider, id=parent.pk)
            if not user.has_perm(perm=VIEW_PROVIDER_UPGRADE_PERM, obj=provider) and not user.has_perm(
                perm=VIEW_PROVIDER_UPGRADE_PERM
            ):
                raise PermissionDenied(f"You can't view upgrades of {provider}")
            return provider

        raise ValueError("Wrong object")

    def get_upgrade(self, parent: Cluster | Provider):
        upgrade = self.get_object()
        if upgrade.bundle.name != parent.prototype.bundle.name:
            raise AdcmEx(code="UPGRADE_NOT_FOUND")

        upgrade_is_allowed, error = check_upgrade(obj=parent, upgrade=upgrade)
        if not upgrade_is_allowed:
            raise AdcmEx(code="UPGRADE_NOT_FOUND", msg=error)

        return upgrade

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        parent: Cluster | Provider = self.get_parent_object_for_user(user=request.user)
        # TODO: This is very not optimal, and requires reworking
        available_upgrades = [upgrade.id for upgrade in get_upgrade(obj=parent)]
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(id__in=available_upgrades))
        serializer = self.get_serializer_class()(instance=queryset, many=True)
        return Response(data=serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        parent: Cluster | Provider = self.get_parent_object_for_user(user=request.user)

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

        parent: Cluster | Provider = self.get_parent_object_for_user(user=request.user)
        upgrade = self.get_upgrade(parent=parent)

        check_hostcomponents_objects_exist(serializer.validated_data["host_component_map"])

        return self._run_new(serializer, upgrade, parent)

    def _run_new(self, serializer: Serializer, upgrade: Upgrade, parent: Cluster | Provider) -> Response:
        data = serializer.validated_data

        configuration = None
        if data["configuration"] is not None:
            config_data = data["configuration"]
            # only when both are not empty, we consider it specified configuration
            if config_data["config"] or config_data["adcm_meta"]:
                configuration = ConfigurationDTO(
                    convert=convert_main_config,
                    input_config={"config": config_data["config"], "attr": config_data["adcm_meta"]},
                )

        mapping = (
            {
                HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                for entry in data["host_component_map"]
            }
            if data["host_component_map"] is None
            else None
        )

        payload = UpgradeActionDTO(
            configuration=configuration,
            mapping=mapping,
            launch=core.job.dto.LaunchOptions(is_blocking=True, is_verbose=data["is_verbose"]),
        )

        config_service = get_config_service()
        wizard_service = get_wizard_service()
        context_gatherer = ContextGatherer(config_service=config_service, wizard_service=wizard_service)

        result = upgrade_object(
            obj=parent,
            upgrade=upgrade,
            payload=payload,
            job_service=get_job_service(),
            config_service=config_service,
            context_gatherer=context_gatherer,
            start_task_after_schedule=not use_new_job_scheduler(),
        )

        match result:
            case ("plain", _):
                return Response(status=HTTP_204_NO_CONTENT)
            case ("task", task_id):
                task_orm = TaskLog.objects.get(pk=task_id)
                return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task_orm).data)
