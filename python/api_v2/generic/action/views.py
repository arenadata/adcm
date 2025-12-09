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

from itertools import compress

from adcm.feature_flags import use_new_job_scheduler
from adcm.mixins import GetParentObjectMixin
from cm.converters import (
    orm_object_to_action_target_descriptor,
    orm_object_to_action_target_type,
    orm_object_to_core_descriptor,
)
from cm.errors import AdcmEx
from cm.legacy.services.job.action import ContextGatherer
from cm.models import (
    Action,
    ADCMEntity,
    ConcernType,
    ConfigHostGroup,
    Host,
    HostComponent,
)
from core.legacy.cluster.types import HostComponentEntry
from core.legacy.job.types import AssociatedProcess
from core.types import ADCMCoreType
from django.conf import settings
from django.db.models import Q
from infra.services import get_config_service, get_job_service, get_wizard_service
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_200_OK,
)
from use_cases.transition.job.schedule import (
    ActionTarget,
    ConfigurationDTO,
    RunActionDTO,
    retrieve_configuration_for_action,
    schedule_task,
)
import core

from api_v2.generic.action.filters import ActionFilter
from api_v2.generic.action.serializers import (
    ActionListSerializer,
    ActionRetrieveSerializer,
    ActionRunSerializer,
)
from api_v2.generic.action.utils import (
    check_process_object,
    filter_actions_by_user_perm,
    get_action_processes,
    has_run_perms,
)
from api_v2.task.serializers import TaskListSerializer
from api_v2.utils.checks import check_hostcomponents_objects_exist
from api_v2.utils.config import add_selection_for_selectable_groups, convert_json_fields_to_strings, convert_main_config
from api_v2.views import ADCMGenericViewSet


class ActionPermissionsMixin:
    def check_permissions_for_list(self, request: Request, parent_object: ADCMEntity) -> None:
        if (
            not parent_object
            or not request.user.has_perm(perm=f"cm.view_{parent_object.__class__.__name__.lower()}")
            and not request.user.has_perm(perm=f"cm.view_{parent_object.__class__.__name__.lower()}", obj=parent_object)
        ):
            raise NotFound()

    def check_permissions_for_run(self, request: Request, action: Action, parent_object: ADCMEntity) -> None:
        if (
            not parent_object
            or not request.user.has_perm(perm=f"cm.view_{parent_object.__class__.__name__.lower()}")
            and not request.user.has_perm(perm=f"cm.view_{parent_object.__class__.__name__.lower()}", obj=parent_object)
            or not has_run_perms(user=request.user, action=action, obj=parent_object)
        ):
            raise NotFound()


class ActionViewSet(
    ListModelMixin, RetrieveModelMixin, GetParentObjectMixin, ADCMGenericViewSet, ActionPermissionsMixin
):
    filterset_class = ActionFilter
    general_queryset = (
        Action.objects.select_related("prototype")
        .exclude(name__in=settings.ADCM_SERVICE_ACTION_NAMES_SET)
        .filter(upgrade__isnull=True)
        .order_by("pk")
    )
    pagination_class = None

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        # Using getattr here for schema generation purposes.
        # There's no `parent_object` attr during that process,
        # so assuming it's absent is a correct path generally speaking.
        if (
            getattr(self, "parent_object", None) is None
            or self.parent_object.concerns.filter(type=ConcernType.LOCK).exists()
        ):
            return Action.objects.none()

        self.prototype_objects = {}

        result_qs = self.general_queryset

        if isinstance(self.parent_object, Host):
            if self.parent_object.cluster:
                self.prototype_objects[self.parent_object.cluster.prototype] = self.parent_object.cluster

                for hc_item in HostComponent.objects.filter(host=self.parent_object).select_related(
                    "service__prototype", "component__prototype"
                ):
                    self.prototype_objects[hc_item.service.prototype] = hc_item.service
                    self.prototype_objects[hc_item.component.prototype] = hc_item.component

            if self.parent_object.original:
                # for host duplicates own actions should be always excluded
                result_qs = result_qs.exclude(host_action=False)

        result_qs = result_qs.filter(
            Q(prototype=self.parent_object.prototype, host_action=False)
            | Q(prototype__in=self.prototype_objects.keys(), host_action=True)
        )

        self.prototype_objects[self.parent_object.prototype] = self.parent_object

        return result_qs

    def get_serializer_class(
        self,
    ) -> type[ActionRetrieveSerializer | ActionListSerializer | ActionRunSerializer]:
        if self.action == "retrieve":
            return ActionRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return ActionListSerializer

    def handle_exception(self, exc: Exception) -> Response:
        # temporal handling
        if isinstance(exc, core.config.OperationError):
            exc = AdcmEx(code="ACTION_OPERATION_ERROR", msg=exc.args[0])

        return super().handle_exception(exc)

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        self.parent_object = self.get_parent_object()

        self.check_permissions_for_list(request=request, parent_object=self.parent_object)

        return self._list_actions_available_to_user(request)

    def retrieve(self, request, *args, **kwargs):  # noqa: ARG002
        self.parent_object = self.get_parent_object()
        action_: Action = self.get_object()

        self.check_permissions_for_run(request=request, action=action_, parent_object=self.parent_object)

        config_schema, config, adcm_meta = self.get_action_configuration_new(
            action=action_, target=self._get_actions_owner()
        )

        # processes = None - If processes are not supported by the action.
        # processes = [] - If processes is supported by the action, but there are no created processes yet.
        # processes = [last created process] - If processes are is supported by the action and the processes exists.
        processes = None

        if action_.wizard_template and orm_object_to_action_target_type(object_=self.parent_object) in (
            ADCMCoreType.CLUSTER,
            ADCMCoreType.SERVICE,
            ADCMCoreType.COMPONENT,
        ):
            processes = get_action_processes(action=action_, object_=orm_object_to_core_descriptor(self.parent_object))

        serializer = self.get_serializer_class()(
            instance=action_,
            context={
                "obj": self.parent_object,
                "config_schema": config_schema,
                "config": config,
                "adcm_meta": adcm_meta,
                "processes": processes,
            },
        )

        return Response(data=serializer.data)

    def get_action_configuration_new(self, action: Action, target: ADCMEntity):
        if not isinstance(target, ActionTarget):
            raise TypeError(f"Can't get configuration for {target=}")

        config_service = get_config_service()

        context_gatherer = ContextGatherer(config_service=config_service, wizard_service=get_wizard_service())
        result = retrieve_configuration_for_action(
            action_orm=action, target=target, config_service=config_service, context_gatherer=context_gatherer
        )

        if not result:
            return None, None, None

        spec, defaults, default_config, owner = result

        jsonschema = config_service.retrieve_jsonschema_for_action(
            action_specification=spec, action_config_defaults=defaults, action_owner=owner
        )
        attributes = {name: {"isActive": attrs.is_active} for name, attrs in default_config.attributes.items()}
        values = convert_json_fields_to_strings(values=default_config.values, spec=spec, inplace=True)
        add_selection_for_selectable_groups(values=values, spec=spec, inplace=True)

        return jsonschema, values, attributes

    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        self.parent_object = self.get_parent_object()
        target_action = self.get_object()
        action_owner = self._get_actions_owner()

        self.check_permissions_for_run(request=request, action=target_action, parent_object=self.parent_object)

        if reason := target_action.get_start_impossible_reason(action_owner):
            raise AdcmEx("ACTION_ERROR", msg=reason)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        check_hostcomponents_objects_exist(serializer.validated_data["host_component_map"])

        if serializer.validated_data["process"]:
            check_process_object(
                process_id=serializer.validated_data["process"]["id"],
                action_id=target_action.id,
                action_target=orm_object_to_action_target_descriptor(object_=self.parent_object),
            )

        task = self._run_new(serializer, target_action)

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)

    def _run_new(self, serializer: Serializer, target_action: Action):
        if self.parent_object is None or isinstance(self.parent_object, ConfigHostGroup):
            raise ValueError(f"Unexpectedly parent object of object is {self.parent_object}")

        config_service = get_config_service()
        job_service = get_job_service()

        data: dict = serializer.validated_data

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
            if data["host_component_map"] is not None
            else None
        )

        process = AssociatedProcess(**data["process"]) if data["process"] else None

        payload = RunActionDTO(
            configuration=configuration,
            mapping=mapping,
            launch=core.legacy.job.dto.LaunchOptions(
                is_blocking=data["should_block_object"],
                is_verbose=data["is_verbose"],
            ),
            process=process,
            description=data["description"],
        )

        context_gatherer = ContextGatherer(config_service=config_service, wizard_service=get_wizard_service())

        return schedule_task(
            action_orm=target_action,
            target=self.parent_object,
            payload=payload,
            job_service=job_service,
            config_service=config_service,
            context_gatherer=context_gatherer,
            start_task_after_schedule=not use_new_job_scheduler(),
        )

    def _list_actions_available_to_user(self, request: Request) -> Response:
        actions = self.filter_queryset(self.get_queryset())
        allowed_actions_mask = [act.allowed(self.prototype_objects[act.prototype]) for act in actions]
        actions = list(compress(actions, allowed_actions_mask))
        actions = filter_actions_by_user_perm(user=request.user, obj=self._get_actions_owner(), actions=actions)

        serializer = self.get_serializer_class()(instance=actions, many=True, context={"obj": self.parent_object})

        return Response(data=serializer.data)

    def _get_actions_owner(self) -> ADCMEntity:
        return self.parent_object
