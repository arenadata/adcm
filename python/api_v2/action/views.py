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

from adcm.mixins import GetParentObjectMixin
from audit.utils import audit
from cm.errors import AdcmEx
from cm.job import ActionRunPayload, run_action
from cm.models import ADCM, Action, ConcernType, Host, HostComponent, PrototypeConfig
from cm.stack import check_hostcomponents_objects_exist
from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from jinja_config import get_jinja_config
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.action.filters import ActionFilter
from api_v2.action.serializers import (
    ActionListSerializer,
    ActionRetrieveSerializer,
    ActionRunSerializer,
)
from api_v2.action.utils import (
    check_run_perms,
    filter_actions_by_user_perm,
    get_action_configuration,
    insert_service_ids,
)
from api_v2.api_schema import ErrorSerializer
from api_v2.config.utils import convert_adcm_meta_to_attr, represent_string_as_json_type
from api_v2.task.serializers import TaskListSerializer
from api_v2.views import CamelCaseGenericViewSet


class ActionViewSet(ListModelMixin, RetrieveModelMixin, GetParentObjectMixin, CamelCaseGenericViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ActionFilter

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        if self.parent_object is None or self.parent_object.concerns.filter(type=ConcernType.LOCK).exists():
            return Action.objects.none()

        self.prototype_objects = {}

        if isinstance(self.parent_object, Host) and self.parent_object.cluster:
            self.prototype_objects[self.parent_object.cluster.prototype] = self.parent_object.cluster

            for hc_item in HostComponent.objects.filter(host=self.parent_object).select_related(
                "service__prototype", "component__prototype"
            ):
                self.prototype_objects[hc_item.service.prototype] = hc_item.service
                self.prototype_objects[hc_item.component.prototype] = hc_item.component

        actions = (
            Action.objects.all()
            .select_related("prototype")
            .exclude(name__in=settings.ADCM_SERVICE_ACTION_NAMES_SET)
            .filter(upgrade__isnull=True)
            .filter(
                Q(prototype=self.parent_object.prototype, host_action=False)
                | Q(prototype__in=self.prototype_objects.keys(), host_action=True)
            )
            .order_by("pk")
        )

        self.prototype_objects[self.parent_object.prototype] = self.parent_object

        return actions

    def get_serializer_class(
        self,
    ) -> type[ActionRetrieveSerializer] | type[ActionListSerializer] | type[ActionRunSerializer]:
        if self.action == "retrieve":
            return ActionRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return ActionListSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        self.parent_object = self.get_parent_object()
        if (
            not self.parent_object
            or not request.user.has_perm(perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}")
            and not request.user.has_perm(
                perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}", obj=self.parent_object
            )
        ):
            raise NotFound()

        actions = self.filter_queryset(self.get_queryset())
        allowed_actions_mask = [act.allowed(self.prototype_objects[act.prototype]) for act in actions]
        actions = list(compress(actions, allowed_actions_mask))
        actions = filter_actions_by_user_perm(user=request.user, obj=self.parent_object, actions=actions)

        serializer = self.get_serializer_class()(instance=actions, many=True, context={"obj": self.parent_object})

        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):  # noqa: ARG002
        self.parent_object = self.get_parent_object()
        action_ = self.get_object()

        if (
            not self.parent_object
            or not request.user.has_perm(perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}")
            and not request.user.has_perm(
                perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}", obj=self.parent_object
            )
            or not check_run_perms(user=request.user, action=action_, obj=self.parent_object)
        ):
            raise NotFound()

        config_schema, config, adcm_meta = get_action_configuration(action_=action_, object_=self.parent_object)

        serializer = self.get_serializer_class()(
            instance=action_,
            context={
                "obj": self.parent_object,
                "config_schema": config_schema,
                "config": config,
                "adcm_meta": adcm_meta,
            },
        )

        return Response(data=serializer.data)

    @audit
    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        self.parent_object = self.get_parent_object()
        target_action = self.get_object()

        if (
            not self.parent_object
            or not request.user.has_perm(perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}")
            and not request.user.has_perm(
                perm=f"cm.view_{self.parent_object.__class__.__name__.lower()}", obj=self.parent_object
            )
            or not check_run_perms(user=request.user, action=target_action, obj=self.parent_object)
        ):
            raise NotFound()

        if reason := target_action.get_start_impossible_reason(self.parent_object):
            raise AdcmEx("ACTION_ERROR", msg=reason)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        configuration = serializer.validated_data["configuration"]
        config = {}
        adcm_meta = {}

        if configuration is not None:
            config = configuration["config"]
            adcm_meta = configuration["adcm_meta"]

        if target_action.config_jinja:
            prototype_configs, _ = get_jinja_config(action=target_action, obj=self.parent_object)
            prototype_configs = [
                prototype_config for prototype_config in prototype_configs if prototype_config.type == "json"
            ]
        else:
            prototype_configs = PrototypeConfig.objects.filter(
                prototype=target_action.prototype, type="json", action=target_action
            ).order_by("pk")

        config = represent_string_as_json_type(prototype_configs=prototype_configs, value=config)
        attr = convert_adcm_meta_to_attr(adcm_meta=adcm_meta)

        check_hostcomponents_objects_exist(serializer.validated_data["host_component_map"])

        task = run_action(
            action=target_action,
            obj=self.parent_object,
            payload=ActionRunPayload(
                conf=config,
                attr=attr,
                hostcomponent=insert_service_ids(hc_create_data=serializer.validated_data["host_component_map"]),
                verbose=serializer.validated_data["is_verbose"],
            ),
            hosts=[],
        )

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)


@extend_schema_view(
    run=extend_schema(
        operation_id="postADCMaction",
        summary="POST adcm action",
        description="Run ADCM action.",
        responses={
            200: TaskListSerializer,
            400: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    ),
    list=extend_schema(
        operation_id="getADCMactions",
        summary="GET adcm actions",
        description="Get a list of ADCM actions.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
                type=str,
            )
        ],
        responses={200: ActionListSerializer, 404: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getADCMaction",
        summary="GET adcm action",
        description="Get information about a specific ADCM action.",
        responses={200: ActionRetrieveSerializer, 404: ErrorSerializer},
    ),
)
class AdcmActionViewSet(ActionViewSet):
    def get_parent_object(self):
        return ADCM.objects.first()
