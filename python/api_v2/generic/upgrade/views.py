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

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_CLUSTER_UPGRADE_PERM,
    VIEW_PROVIDER_PERM,
    VIEW_PROVIDER_UPGRADE_PERM,
    check_custom_perm,
    get_object_for_user,
)
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.legacy.upgrade import DifferentBundleError, check_upgrade, get_upgrade
from cm.models import Bundle, Cluster, ObjectType, Prototype, Provider, TaskLog, Upgrade
from cm.transition.action import RetrieveStartImpossibleReason
from core.legacy.cluster.types import HostComponentEntry
from core.types import Descriptor
from dishka import FromDishka
from django.db.models import OuterRef, Prefetch, Subquery
from rbac.models import User
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from use_cases.dto import ConfigurationDTO, UpgradeActionDTO
from use_cases.transition.job.schedule import RetrieveConfigurationForAction
from use_cases.transition.upgrade import UpgradeObject
import core

from api_v2.generic.action.serializers import UpgradeRunSerializer
from api_v2.generic.upgrade.filters import UpgradeFilter
from api_v2.generic.upgrade.serializers import UpgradeListSerializer, UpgradeRetrieveSerializer
from api_v2.task.serializers import TaskListSerializer
from api_v2.utils.config import convert_json_fields_to_strings, convert_main_config
from api_v2.utils.di import inject
from api_v2.views import ADCMGenericViewSet


class UpgradeViewSet(ListModelMixin, GetParentObjectMixin, RetrieveModelMixin, ADCMGenericViewSet):
    queryset = Upgrade.objects.select_related("action", "action__prototype")
    filterset_class = UpgradeFilter
    pagination_class = None
    exc_conversion_map = {
        core.config.ConfigOperationError: "UPGRADE_OPERATION_ERROR",
        DifferentBundleError: "UPGRADE_NOT_FOUND",  # ADCM-7976
    }

    def handle_exception(self, exc: Exception) -> Response:
        if exc_code := self.exc_conversion_map.get(exc.__class__):
            exc = AdcmEx(code=exc_code, msg=exc.args[0] if exc.args else "")

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
        parent = self.get_parent_object()
        match parent:
            case Cluster():
                cluster = get_object_for_user(user=user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=parent.pk)

                if not user.has_perm(perm=VIEW_CLUSTER_UPGRADE_PERM, obj=cluster) and not user.has_perm(
                    perm=VIEW_CLUSTER_UPGRADE_PERM
                ):
                    raise PermissionDenied(f"You can't view upgrades of {cluster}")

                return cluster

            case Provider():
                provider = get_object_for_user(user=user, perms=VIEW_PROVIDER_PERM, klass=Provider, id=parent.pk)

                if not user.has_perm(perm=VIEW_PROVIDER_UPGRADE_PERM, obj=provider) and not user.has_perm(
                    perm=VIEW_PROVIDER_UPGRADE_PERM
                ):
                    raise PermissionDenied(f"You can't view upgrades of {provider}")

                return provider

            case None:
                message = "Can't find upgrade's parent object"
                raise NotFound(message)

            case _:
                raise ValueError("Wrong object")

    @inject
    def list(
        self,
        request: Request,
        *args,  # noqa: ARG001, ARG002
        retrieve_sir: FromDishka[RetrieveStartImpossibleReason],
        **kwargs,  # noqa: ARG001, ARG002
    ) -> Response:
        parent = self.get_parent_object_for_user(user=request.user)
        # TODO: This is very not optimal, and requires reworking
        available_upgrades = [upgrade.id for upgrade in get_upgrade(obj=parent)]
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(id__in=available_upgrades))

        start_impossible_reason = retrieve_sir.for_upgrade_target(
            target=Descriptor(id=parent.id, type=orm_object_to_core_type(parent))
        )
        serializer = self.get_serializer_class()(
            instance=queryset, many=True, context={"start_impossible_reason": start_impossible_reason}
        )

        return Response(data=serializer.data)

    @inject
    def retrieve(
        self,
        request: Request,
        retrieve_configuration: FromDishka[RetrieveConfigurationForAction],
        config_service: FromDishka[core.config.ConfigService],
        retrieve_sir: FromDishka[RetrieveStartImpossibleReason],
        **_,
    ) -> Response:  # noqa: ARG001, ARG002
        parent_orm: Cluster | Provider = self.get_parent_object_for_user(user=request.user)
        upgrade = self.get_object()

        # for retrieve endpoint start_impossible_reason should not cause an exception
        success, msg = check_upgrade(obj=parent_orm, upgrade=upgrade, retrieve_sir=None)
        if not success:
            raise AdcmEx(code="UPGRADE_NOT_FOUND", msg=msg)

        start_impossible_reason = retrieve_sir.for_upgrade_target(
            target=Descriptor(id=parent_orm.id, type=orm_object_to_core_type(parent_orm))
        )

        jsonschema = None
        config = None
        adcm_meta = None

        if upgrade.action:
            result = retrieve_configuration.do(action_orm=upgrade.action, target=parent_orm)
            if result:
                spec, defaults, default_config, owner = result
                adcm_meta = {name: {"isActive": attrs.is_active} for name, attrs in default_config.attributes.items()}
                config = convert_json_fields_to_strings(values=default_config.values, spec=spec, inplace=True)
                jsonschema = config_service.retrieve_jsonschema_for_action(
                    action_specification=spec, action_config_defaults=defaults, action_owner=owner
                )

        serializer = self.get_serializer_class()(
            instance=upgrade,
            context={
                "parent": parent_orm,
                "config_schema": jsonschema,
                "config": config,
                "adcm_meta": adcm_meta,
                "start_impossible_reason": start_impossible_reason,
            },
        )

        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    @inject
    def run(
        self,
        request: Request,
        *_,
        upgrade_object: FromDishka[UpgradeObject],
        **__,
    ) -> Response:
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        data: dict = serializer.validated_data
        parent_orm: Cluster | Provider = self.get_parent_object_for_user(user=request.user)
        upgrade = self.get_object()

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

        result = upgrade_object.do(
            target=parent_orm,
            upgrade=upgrade,
            payload=payload,
        )

        match result:
            case ("plain", _):
                return Response(status=HTTP_204_NO_CONTENT)
            case ("task", task_id):
                task_orm = TaskLog.objects.get(pk=task_id)
                return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task_orm).data)
