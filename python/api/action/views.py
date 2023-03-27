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
import hashlib
from itertools import compress

from api.action.serializers import (
    ActionDetailSerializer,
    ActionSerializer,
    ActionUISerializer,
)
from api.base_view import GenericUIView
from api.job.serializers import RunTaskRetrieveSerializer
from api.utils import AdcmFilterBackend, create, filter_actions, get_object_for_user
from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import Action, Host, HostComponent, TaskLog, get_model_by_type
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from rbac.viewsets import DjangoOnlyObjectPermissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

VIEW_ACTION_PERM = "cm.view_action"


def get_object_type_id(**kwargs) -> tuple[str, int, int]:
    object_type = kwargs.get("object_type")
    object_id = kwargs.get(f"{object_type}_id") or kwargs.get(f"{object_type}_pk")
    action_id = kwargs.get("action_id", None)

    return object_type, object_id, action_id


def get_obj(**kwargs):
    object_type, object_id, action_id = get_object_type_id(**kwargs)
    model = get_model_by_type(object_type)
    obj = model.obj.get(id=object_id)

    return obj, action_id


class ActionList(PermissionListMixin, GenericUIView):
    queryset = Action.objects.filter(upgrade__isnull=True).exclude(name__in=settings.ADCM_SERVICE_ACTION_NAMES_SET)
    serializer_class = ActionSerializer
    serializer_class_ui = ActionUISerializer
    filterset_fields = ("name",)
    filter_backends = (AdcmFilterBackend,)
    permission_required = [VIEW_ACTION_PERM]

    def _get_actions_for_host(self, host: Host) -> set[Action]:
        actions = set(filter_actions(host, self.filter_queryset(self.get_queryset().filter(prototype=host.prototype))))
        hostcomponents = HostComponent.objects.filter(host_id=host.id)
        if hostcomponents:
            for hostcomponent in hostcomponents:
                cluster, _ = get_obj(object_type="cluster", cluster_id=hostcomponent.cluster_id)
                service, _ = get_obj(object_type="service", service_id=hostcomponent.service_id)
                component, _ = get_obj(object_type="component", component_id=hostcomponent.component_id)
                for connect_obj in [cluster, service, component]:
                    actions.update(
                        filter_actions(
                            connect_obj,
                            self.filter_queryset(
                                self.get_queryset().filter(prototype=connect_obj.prototype, host_action=True),
                            ),
                        ),
                    )
        else:
            if host.cluster is not None:
                actions.update(
                    filter_actions(
                        host.cluster,
                        self.filter_queryset(
                            self.get_queryset().filter(prototype=host.cluster.prototype, host_action=True),
                        ),
                    ),
                )

        return actions

    def get(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        if kwargs["object_type"] == "host":
            host, _ = get_obj(object_type="host", host_id=kwargs["host_id"])
            actions = self._get_actions_for_host(host)

            obj = host
            objects = {"host": host}
        else:
            obj, _ = get_obj(**kwargs)
            actions = filter_actions(
                obj,
                self.filter_queryset(self.get_queryset().filter(prototype=obj.prototype, host_action=False)),
            )
            objects = {obj.prototype.type: obj}

        # added filter actions by custom perm for run actions
        perms = [f"cm.run_action_{hashlib.sha256(a.name.encode(settings.ENCODING_UTF_8)).hexdigest()}" for a in actions]
        mask = [request.user.has_perm(perm, obj) for perm in perms]
        actions = list(compress(actions, mask))

        serializer = self.get_serializer(
            actions,
            many=True,
            context={"request": request, "objects": objects, "obj": obj},
        )

        return Response(serializer.data)


class ActionDetail(PermissionListMixin, GenericUIView):
    queryset = Action.objects.filter(upgrade__isnull=True)
    serializer_class = ActionDetailSerializer
    serializer_class_ui = ActionUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = [VIEW_ACTION_PERM]

    def get(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        object_type, object_id, action_id = get_object_type_id(**kwargs)
        model = get_model_by_type(object_type)
        content_type = ContentType.objects.get_for_model(model)
        obj = get_object_for_user(
            request.user,
            f"{content_type.app_label}.view_{content_type.model}",
            model,
            id=object_id,
        )
        action = get_object_for_user(
            request.user,
            VIEW_ACTION_PERM,
            self.get_queryset(),
            id=action_id,
        )
        if isinstance(obj, Host) and action.host_action:
            objects = {"host": obj}
        else:
            objects = {action.prototype.type: obj}

        serializer = self.get_serializer(action, context={"request": request, "objects": objects, "obj": obj})

        return Response(serializer.data)


class RunTask(GenericUIView):
    queryset = TaskLog.objects.all()
    serializer_class = RunTaskRetrieveSerializer
    permission_classes = (IsAuthenticated,)

    def has_action_perm(self, action: Action, obj) -> bool:
        user = self.request.user

        if user.has_perm("cm.add_task"):
            return True

        action_name = hashlib.sha256(action.name.encode(settings.ENCODING_UTF_8)).hexdigest()

        return user.has_perm(f"cm.run_action_{action_name}", obj)

    def check_action_perm(self, action: Action, obj) -> None:
        if not self.has_action_perm(action, obj):
            raise PermissionDenied()

    @audit
    def post(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        object_type, object_id, action_id = get_object_type_id(**kwargs)
        model = get_model_by_type(object_type)
        content_type = ContentType.objects.get_for_model(model)
        obj = get_object_for_user(
            request.user,
            f"{content_type.app_label}.view_{content_type.model}",
            model,
            id=object_id,
        )
        action = get_object_for_user(request.user, VIEW_ACTION_PERM, Action, id=action_id)
        if reason := action.get_start_impossible_reason(obj):
            raise AdcmEx("ACTION_ERROR", msg=reason)

        self.check_action_perm(action, obj)
        serializer = self.get_serializer(data=request.data)

        return create(serializer, action=action, task_object=obj)
