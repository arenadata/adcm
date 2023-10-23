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
from cm.models import Action, ConcernType, Host, HostComponent
from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
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
    queryset = (
        Action.objects.select_related("prototype")
        .filter(upgrade__isnull=True)
        .exclude(name__in=settings.ADCM_SERVICE_ACTION_NAMES_SET)
        .order_by("pk")
    )
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ActionFilter

    def get_serializer_class(
        self,
    ) -> type[ActionRetrieveSerializer] | type[ActionListSerializer] | type[ActionRunSerializer]:
        if self.action == "retrieve":
            return ActionRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return ActionListSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        parent_object = self.get_parent_object()

        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        if parent_object.concerns.filter(type=ConcernType.LOCK).exists():
            return Response(data=[])

        prototype_object = {}

        if isinstance(parent_object, Host) and parent_object.cluster:
            prototype_object[parent_object.cluster.prototype] = parent_object.cluster

            for hc_item in HostComponent.objects.filter(host=parent_object).select_related(
                "service__prototype", "component__prototype"
            ):
                prototype_object[hc_item.service.prototype] = hc_item.service
                prototype_object[hc_item.component.prototype] = hc_item.component

        actions = self.filter_queryset(
            self.get_queryset().filter(
                Q(prototype=parent_object.prototype, host_action=False)
                | Q(prototype__in=prototype_object.keys(), host_action=True)
            )
        )
        prototype_object[parent_object.prototype] = parent_object

        allowed_actions_mask = [act.allowed(prototype_object[act.prototype]) for act in actions]
        actions = list(compress(actions, allowed_actions_mask))
        actions = filter_actions_by_user_perm(user=request.user, obj=parent_object, actions=actions)

        serializer = self.get_serializer_class()(instance=actions, many=True, context={"obj": parent_object})

        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        # check permissions
        get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=kwargs["pk"])

        action_ = self.get_object()

        schema = None
        adcm_meta = None

        if not action_.config_jinja:  # TODO add schema and adcm_meta from jinja config ADCM-4620
            schema = get_config_schema(object_=parent_object, action=action_)
            _, _, _, attr = get_prototype_config(prototype=action_.prototype, action=action_)
            if attr and schema:
                adcm_meta = convert_attr_to_adcm_meta(attr=attr)

        serializer = self.get_serializer_class()(
            instance=action_, context={"obj": parent_object, "config_schema": schema, "adcm_meta": adcm_meta}
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

        task = start_task(
            action=target_action,
            obj=parent_object,
            conf=represent_string_as_json_type(
                prototype=target_action.prototype, value=serializer.validated_data["config"], action=target_action
            ),
            attr=convert_adcm_meta_to_attr(adcm_meta=serializer.validated_data["adcm_meta"]),
            hostcomponent=insert_service_ids(hc_create_data=serializer.validated_data["host_component_map"]),
            hosts=[],
            verbose=serializer.validated_data["is_verbose"],
        )

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)
