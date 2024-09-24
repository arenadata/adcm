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

from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from typing import Any, TypeAlias
import json

from audit.alt.core import AuditedCallArguments, IDBasedAuditObjectCreator, OperationAuditContext, Result
from audit.alt.hooks import AuditHook
from audit.alt.object_retrievers import GeneralAuditObjectRetriever
from audit.models import AuditObject, AuditObjectType
from cm.converters import core_type_to_model, model_name_to_audit_object_type, model_name_to_core_type
from cm.models import (
    ADCM,
    ADCMCoreType,
    Bundle,
    Cluster,
    Host,
    HostProvider,
    JobLog,
    Prototype,
    Service,
    ServiceComponent,
    TaskLog,
)
from cm.utils import get_obj_type
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Model, Prefetch
from django.http.request import RawPostDataException
from rbac.models import Group, Policy, Role, User
from rest_framework.response import Response

# object retrievers


ObjectField: TypeAlias = str
CallArgument: TypeAlias = str


@dataclass(slots=True)
class ExtractID:
    field: str

    def from_response(self, call_arguments: AuditedCallArguments, result: Result | None):  # noqa: ARG002
        if not isinstance(result, Response):
            return None

        return result.data.get(self.field)

    def from_lookup_kwargs(self, call_arguments: AuditedCallArguments, result: Response | None):  # noqa: ARG002
        return call_arguments.get(self.field)


@dataclass(slots=True)
class ServiceAuditObjectCreator(IDBasedAuditObjectCreator):
    model = Service
    name_field = "prototype__display_name"

    def get_name(self, id_: str | int) -> str | None:
        names = Service.objects.values_list("cluster__name", "prototype__display_name").filter(id=id_).first()
        if not names:
            return None

        return "/".join(names)


@dataclass(slots=True)
class ComponentAuditObjectCreator(IDBasedAuditObjectCreator):
    model = ServiceComponent
    name_field = "prototype__display_name"

    def get_name(self, id_: str | int) -> str | None:
        names = (
            ServiceComponent.objects.values_list(
                "cluster__name", "service__prototype__display_name", "prototype__display_name"
            )
            .filter(id=id_)
            .first()
        )
        if not names:
            return None

        return "/".join(names)


create_audit_cluster_object = IDBasedAuditObjectCreator(model=Cluster)
create_audit_host_object = IDBasedAuditObjectCreator(model=Host, name_field="fqdn")
create_audit_user_object = IDBasedAuditObjectCreator(model=User, name_field="username")
create_audit_group_object = IDBasedAuditObjectCreator(model=Group)
create_audit_policy_object = IDBasedAuditObjectCreator(model=Policy)
create_audit_role_object = IDBasedAuditObjectCreator(model=Role)

bundle_from_lookup = GeneralAuditObjectRetriever(
    audit_object_type=AuditObjectType.BUNDLE,
    create_new=IDBasedAuditObjectCreator(model=Bundle),
    extract_id=ExtractID(field="pk").from_lookup_kwargs,
)

_extract_cluster_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.CLUSTER, create_new=create_audit_cluster_object
)
cluster_from_response = _extract_cluster_from(extract_id=ExtractID(field="id").from_response)
cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="cluster_pk").from_lookup_kwargs)

_extract_service_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.SERVICE,
    create_new=ServiceAuditObjectCreator(model=Service),
)
parent_service_from_lookup = _extract_service_from(extract_id=ExtractID(field="service_pk").from_lookup_kwargs)
service_from_lookup = _extract_service_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)

_extract_component_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.COMPONENT,
    create_new=ComponentAuditObjectCreator(model=ServiceComponent),
)
parent_component_from_lookup = _extract_component_from(extract_id=ExtractID(field="component_pk").from_lookup_kwargs)
component_from_lookup = _extract_component_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)

_extract_hostprovider_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.PROVIDER,
    create_new=IDBasedAuditObjectCreator(model=HostProvider),
)
parent_hostprovider_from_lookup = _extract_hostprovider_from(
    extract_id=ExtractID(field="hostprovider_pk").from_lookup_kwargs
)
hostprovider_from_lookup = _extract_hostprovider_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
hostprovider_from_response = _extract_hostprovider_from(extract_id=ExtractID(field="id").from_response)

_extract_host_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.HOST, create_new=create_audit_host_object
)
host_from_lookup = _extract_host_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
host_from_response = _extract_host_from(extract_id=ExtractID(field="id").from_response)
parent_host_from_lookup = _extract_host_from(extract_id=ExtractID(field="host_pk").from_lookup_kwargs)

_extract_user_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.USER, create_new=create_audit_user_object
)


@dataclass
class ProfileRetriever(GeneralAuditObjectRetriever):
    def __call__(
        self,
        context: "OperationAuditContext",
        call_arguments: AuditedCallArguments,  # noqa: ARG002
        result: Result | None,  # noqa: ARG002
        exception: Exception | None,  # noqa: ARG002
    ) -> AuditObject | None:
        id_ = str(context.user.id) if context.user else None
        if not id_:
            return None

        audit_object = AuditObject.objects.filter(
            object_id=id_, object_type=self.audit_object_type, is_deleted=self.is_deleted
        ).first()
        if audit_object:
            return audit_object

        return self.create_new(id_, self.audit_object_type)


_extract_profile_from = partial(
    ProfileRetriever, audit_object_type=AuditObjectType.USER, create_new=create_audit_user_object
)
user_from_response = _extract_user_from(extract_id=ExtractID(field="id").from_response)
user_from_lookup = _extract_user_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
profile_of_current_user = _extract_profile_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)

_extract_group_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.GROUP, create_new=create_audit_group_object
)
group_from_response = _extract_group_from(extract_id=ExtractID(field="id").from_response)
group_from_lookup = _extract_group_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)

_extract_policy_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.POLICY, create_new=create_audit_policy_object
)
policy_from_response = _extract_policy_from(extract_id=ExtractID(field="id").from_response)
policy_from_lookup = _extract_policy_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)

_extract_role_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.ROLE, create_new=create_audit_role_object
)
role_from_response = _extract_role_from(extract_id=ExtractID(field="id").from_response)
role_from_lookup = _extract_role_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)


def adcm_audit_object(
    context: "OperationAuditContext",  # noqa: ARG001
    call_arguments: AuditedCallArguments,  # noqa: ARG001
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> AuditObject:
    adcm = AuditObject.objects.filter(object_type=AuditObjectType.ADCM, is_deleted=False).first()
    if adcm:
        return adcm

    return AuditObject.objects.create(
        object_id=ADCM.objects.values_list("id", flat=True).first(),
        object_name="ADCM",
        object_type=AuditObjectType.ADCM,
        is_deleted=False,
    )


# hooks


def update_cluster_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = Cluster.objects.values_list("name", flat=True).filter(id=instance.object_id).first()
    if not new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


def update_user_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = User.objects.values_list("username", flat=True).filter(id=instance.object_id).first()
    if not new_name or instance.object_name == new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


def update_group_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = Group.objects.values_list("name", flat=True).filter(id=instance.object_id).first()
    if not new_name or instance.object_name == new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


def update_policy_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = Policy.objects.values_list("name", flat=True).filter(id=instance.object_id).first()
    if not new_name or instance.object_name == new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


def update_role_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = Role.objects.values_list("name", flat=True).filter(id=instance.object_id).first()
    if not new_name or instance.object_name == new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


# hook helpers / special functions


def _retrieve_request_body(request: WSGIRequest) -> Any | None:
    if not request:
        return None

    # request's body can be read only once
    body = None
    with suppress(AttributeError, json.JSONDecodeError, RawPostDataException):
        body = json.loads(request.body)

    return body


def object_does_exist(
    hook: AuditHook,
    model: type[Model],
    id_field: str = "pk",
    arg_model_field_map: dict[CallArgument, ObjectField] | None = None,
) -> bool:
    id_ = hook.call_arguments.get(id_field)
    if not id_:
        # it's quite a stretch, but I don't see an alternative way for a safe implementation here
        return False

    lookup_kwargs = (
        {
            object_field: hook.call_arguments.get(call_argument)
            for call_argument, object_field in arg_model_field_map.items()
        }
        if arg_model_field_map
        else {}
    )

    return model.objects.filter(id=id_, **lookup_kwargs).exists()


def nested_host_does_exist(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Host)


def service_does_exist(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Service)


service_with_parents_specified_in_path_exists = partial(
    object_does_exist, model=Service, arg_model_field_map={"cluster_pk": "cluster_id"}
)

component_with_parents_specified_in_path_exists = partial(
    object_does_exist,
    model=ServiceComponent,
    arg_model_field_map={"cluster_pk": "cluster_id", "service_pk": "service_id"},
)


def retrieve_user_password_groups(id_: int) -> dict:
    if (user := User.objects.filter(pk=id_).first()) is None:
        return {}

    return {"password": user.password, "group": list(user.groups.values_list("name", flat=True).order_by("name"))}


def retrieve_group_name_users(id_: int) -> dict:
    if (group := Group.objects.prefetch_related("user_set").filter(pk=id_).first()) is None:
        return {}

    return {
        "name": group.display_name,
        "user": sorted(user.username for user in group.user_set.all()),
    }


def retrieve_policy_role_object_group(id_: int) -> dict:
    if (policy := Policy.objects.prefetch_related("group", "object").filter(pk=id_).first()) is None:
        return {}

    return {
        "role": policy.role.display_name if policy.role else "",
        "object": [
            {"id": obj.object.pk, "name": obj.object.name, "type": get_obj_type(obj.content_type.name)}
            for obj in policy.object.all()
        ],
        "group": sorted(group.name for group in policy.group.all()),
    }


def retrieve_role_children(id_: int) -> dict:
    prefetch_child_roles = Prefetch("child", queryset=Role.objects.only("display_name"))
    if (role := Role.objects.prefetch_related(prefetch_child_roles).filter(pk=id_).only("id").first()) is None:
        return {}

    return {"child": sorted(child_role.display_name for child_role in role.child.all())}


# name changers


class set_add_hosts_name(AuditHook):  # noqa: N801
    def __call__(self):
        request = self.call_arguments.get("request", "")
        data = _retrieve_request_body(request=request)

        host_fqdn = ""
        if isinstance(data, list):
            # we may want to consider both naming styles here, but just v2-like camelCase for now
            ids = (entry.get("hostId", entry.get("host_id")) for entry in data if isinstance(entry, dict))
            host_fqdn = ", ".join(sorted(Host.objects.filter(id__in=ids).values_list("fqdn", flat=True)))
        elif isinstance(data, dict) and (host_id := data.get("hostId", data.get("host_id"))) is not None:
            host_fqdn = Host.objects.values_list("fqdn", flat=True).filter(id=host_id).first() or ""

        self.context.name = f"[{host_fqdn}] host(s) added"


class set_removed_host_name(AuditHook):  # noqa: N801
    def __call__(self):
        host_id = self.call_arguments.get("pk")

        if not host_id:
            return

        fqdn = Host.objects.values_list("fqdn", flat=True).filter(id=host_id).first() or ""
        self.context.name = f"{fqdn} host removed".strip()


class set_username_for_block_actions(AuditHook):  # noqa: N801
    def __call__(self):
        user_id = self.call_arguments.get("pk")
        username = User.objects.values_list("username", flat=True).filter(id=user_id).first() or ""

        self.context.name = self.context.name.format(username=username).strip()


def update_host_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> None:
    _ = call_arguments, result, exception

    if not context.object:
        return

    instance = context.object

    new_name = Host.objects.values_list("fqdn", flat=True).filter(id=instance.object_id).first()

    if not new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


class set_service_names_from_request(AuditHook):  # noqa: N801
    def __call__(self):
        ids = self._get_ids_from_request(request=self.call_arguments.get("request"))
        service_display_names = (
            Prototype.objects.filter(pk__in=ids).order_by("display_name").values_list("display_name", flat=True)
        )

        service_display_names = ", ".join(service_display_names)

        self.context.name = self.context.name.format(service_names=f"[{service_display_names}]").strip()

    @staticmethod
    def _get_ids_from_request(request: WSGIRequest) -> tuple:
        if request is None:
            return ()

        if (data := _retrieve_request_body(request=request)) is None:
            return ()

        ids = ()
        if isinstance(data, list):
            ids = (entry.get("prototypeId", entry.get("prototype_id")) for entry in data if isinstance(entry, dict))
        elif isinstance(data, dict) and (prototype_id := data.get("prototypeId", data.get("prototype_id"))) is not None:
            ids = (prototype_id,)

        return ids


def set_service_name_from_object(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> None:
    service_name = (
        Service.objects.filter(pk=call_arguments.get("pk"))
        .select_related("prototype__display_name")
        .only("prototype__display_name")
        .values_list("prototype__display_name", flat=True)
        .first()
        or ""
    )

    context.name = context.name.format(service_name=service_name).strip()


def detect_object_for_job(
    context: OperationAuditContext,  # noqa: ARG001
    call_arguments: AuditedCallArguments,
    result: Response | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> AuditObject | None:
    try:
        object_id, model_name = (
            JobLog.objects.filter(id=call_arguments["pk"])
            .values_list("task__object_id", "task__object_type__model")
            .first()
        )
    except TypeError:  # this error is returned to unpack None, which can return if the object is not found
        return None

    model = core_type_to_model(core_type=model_name_to_core_type(model_name=model_name))

    if not model.objects.filter(id=object_id).exists():
        return None

    name = get_audit_object_name(object_id=object_id, model_name=model_name)

    return AuditObject.objects.filter(
        object_id=object_id,
        object_type=model_name_to_audit_object_type(model_name=model_name),
        object_name=name,
    ).first()


def detect_object_for_task(
    context: OperationAuditContext,  # noqa: ARG001
    call_arguments: AuditedCallArguments,
    result: Response | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> AuditObject | None:
    try:
        object_id, model_name = (
            TaskLog.objects.filter(id=call_arguments["pk"]).values_list("object_id", "object_type__model").first()
        )
    except TypeError:  # this error is returned to unpack None, which can return if the object is not found
        return None

    model = core_type_to_model(core_type=model_name_to_core_type(model_name=model_name))

    if not model.objects.filter(id=object_id).exists():
        return None

    name = get_audit_object_name(object_id=object_id, model_name=model_name)

    return AuditObject.objects.filter(
        object_id=object_id,
        object_type=model_name_to_audit_object_type(model_name=model_name),
        object_name=name,
    ).first()


def set_job_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> None:
    job_name = (
        JobLog.objects.select_related("task__action")
        .values_list("task__action__display_name", flat=True)
        .filter(id=call_arguments["pk"])
        .first()
    )

    if job_name is None:
        job_name = "Job"

    context.name = context.name.format(job_name=job_name).strip()


def set_task_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
) -> None:
    task_name = (
        TaskLog.objects.select_related("action")
        .values_list("action__display_name", flat=True)
        .filter(id=call_arguments["pk"])
        .first()
    )

    if task_name is None:
        task_name = "Task"

    context.name = context.name.format(task_name=task_name).strip()


def get_audit_object_name(object_id: int, model_name: str) -> str:
    core_type = model_name_to_core_type(model_name=model_name)

    match core_type:
        case ADCMCoreType.CLUSTER:
            names = Cluster.objects.values_list("name").filter(id=object_id).first()
        case ADCMCoreType.SERVICE:
            names = Service.objects.values_list("cluster__name", "prototype__display_name").filter(id=object_id).first()
        case ADCMCoreType.COMPONENT:
            names = (
                ServiceComponent.objects.values_list(
                    "cluster__name", "service__prototype__display_name", "prototype__display_name"
                )
                .filter(id=object_id)
                .first()
            )
        case ADCMCoreType.HOSTPROVIDER:
            names = HostProvider.objects.values_list("name").filter(id=object_id).first()
        case ADCMCoreType.HOST:
            names = Host.objects.values_list("fqdn").filter(id=object_id).first()
        case _:
            raise ValueError(f"Unsupported core type: {core_type}")

    return "/".join(names or ())
