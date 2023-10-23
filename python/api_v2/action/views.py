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

from api_v2.action.filters import ActionFilter
from api_v2.action.serializers import (
    ActionListSerializer,
    ActionRetrieveSerializer,
    ActionRunSerializer,
)
from api_v2.action.utils import (
    check_run_perms,
    filter_actions_by_user_perm,
    insert_service_ids,
)
from api_v2.config.utils import (
    convert_adcm_meta_to_attr,
    convert_attr_to_adcm_meta,
    get_config_schema,
    represent_string_as_json_type,
)
from api_v2.task.serializers import TaskListSerializer
from api_v2.views import CamelCaseGenericViewSet
from audit.utils import audit
from cm.adcm_config.config import get_prototype_config
from cm.errors import AdcmEx
from cm.job import start_task
from cm.models import ADCM, Action, ConcernType, Host, HostComponent, PrototypeConfig
from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from jinja_config import get_jinja_config
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_ACTION_PERM,
    DjangoModelPermissionsAudit,
    get_object_for_user,
)


class ActionViewSet(  # pylint: disable=too-many-ancestors
    PermissionListMixin, ListModelMixin, RetrieveModelMixin, GetParentObjectMixin, CamelCaseGenericViewSet
):
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ActionFilter

    def get_queryset(self, *args, **kwargs):
        self.parent_object = self.get_parent_object()  # pylint: disable=attribute-defined-outside-init

        if self.parent_object is None:
            raise NotFound("Can't find action's parent object")

        if self.parent_object.concerns.filter(type=ConcernType.LOCK).exists():
            return Action.objects.none()

        self.prototype_objects = {}  # pylint: disable=attribute-defined-outside-init

        if isinstance(self.parent_object, Host) and self.parent_object.cluster:
            self.prototype_objects[self.parent_object.cluster.prototype] = self.parent_object.cluster

            for hc_item in HostComponent.objects.filter(host=self.parent_object).select_related(
                "service__prototype", "component__prototype"
            ):
                self.prototype_objects[hc_item.service.prototype] = hc_item.service
                self.prototype_objects[hc_item.component.prototype] = hc_item.component

        actions = (
            Action.objects.select_related("prototype")
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

    def list(self, request: Request, *args, **kwargs) -> Response:
        actions = self.filter_queryset(self.get_queryset())
        allowed_actions_mask = [act.allowed(self.prototype_objects[act.prototype]) for act in actions]
        actions = list(compress(actions, allowed_actions_mask))
        actions = filter_actions_by_user_perm(user=request.user, obj=self.parent_object, actions=actions)

        serializer = self.get_serializer_class()(instance=actions, many=True, context={"obj": self.parent_object})

        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        action_ = self.get_object()

        # check permissions
        get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=action_.pk)

        if action_.config_jinja:
            prototype_configs, attr = get_jinja_config(action=action_, obj=self.parent_object)
        else:
            prototype_configs = PrototypeConfig.objects.filter(prototype=action_.prototype, action=action_).order_by(
                "pk"
            )
            _, _, _, attr = get_prototype_config(prototype=action_.prototype, action=action_)

        if prototype_configs:
            schema = get_config_schema(object_=self.parent_object, prototype_configs=prototype_configs)
            adcm_meta = convert_attr_to_adcm_meta(attr=attr)
        else:
            schema = None
            adcm_meta = None

        serializer = self.get_serializer_class()(
            instance=action_, context={"obj": self.parent_object, "config_schema": schema, "adcm_meta": adcm_meta}
        )

        return Response(data=serializer.data)

    @audit
    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        target_action = get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=kwargs["pk"])

        if reason := target_action.get_start_impossible_reason(parent_object):
            raise AdcmEx("ACTION_ERROR", msg=reason)

        if not check_run_perms(user=request.user, action=target_action, obj=parent_object):
            return Response(data="Run action forbidden", status=HTTP_403_FORBIDDEN)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        configuration = serializer.validated_data["configuration"]
        config = {}
        adcm_meta = {}

        if configuration is not None:
            config = configuration["config"]
            adcm_meta = configuration["adcm_meta"]

        if target_action.config_jinja:
            prototype_configs, _ = get_jinja_config(action=target_action, obj=parent_object)
            prototype_configs = [
                prototype_config for prototype_config in prototype_configs if prototype_config.type == "json"
            ]
        else:
            prototype_configs = PrototypeConfig.objects.filter(
                prototype=target_action.prototype, type="json", action=target_action
            ).order_by("pk")

        config = represent_string_as_json_type(prototype_configs=prototype_configs, value=config)
        attr = convert_adcm_meta_to_attr(adcm_meta=adcm_meta)

        task = start_task(
            action=target_action,
            obj=parent_object,
            conf=config,
            attr=attr,
            hostcomponent=insert_service_ids(hc_create_data=serializer.validated_data["host_component_map"]),
            hosts=[],
            verbose=serializer.validated_data["is_verbose"],
        )

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)


class AdcmActionViewSet(ActionViewSet):  # pylint: disable=too-many-ancestors
    def get_parent_object(self):
        return ADCM.objects.first()
