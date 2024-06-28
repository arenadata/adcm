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
import json

from audit.alt.core import AuditedCallArguments, IDBasedAuditObjectCreator, OperationAuditContext, Result
from audit.alt.hooks import AuditHook
from audit.alt.object_retrievers import GeneralAuditObjectRetriever
from audit.models import AuditObject, AuditObjectType
from cm.models import ADCM, Bundle, Cluster, ClusterObject, Host, HostProvider, ServiceComponent
from django.db.models import Model
from rbac.models import User
from rest_framework.response import Response

# object retrievers


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
    model = ClusterObject
    name_field = "prototype__display_name"

    def get_name(self, id_: str | int) -> str | None:
        names = ClusterObject.objects.values_list("cluster__name", "prototype__display_name").filter(id=id_).first()
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


_extract_cluster_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.CLUSTER, create_new=create_audit_cluster_object
)
cluster_from_response = _extract_cluster_from(extract_id=ExtractID(field="id").from_response)
cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="cluster_pk").from_lookup_kwargs)

_extract_service_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.SERVICE,
    create_new=ServiceAuditObjectCreator(model=ClusterObject),
)
parent_service_from_lookup = _extract_service_from(extract_id=ExtractID(field="service_pk").from_lookup_kwargs)

_extract_component_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.COMPONENT,
    create_new=ComponentAuditObjectCreator(model=ServiceComponent),
)
parent_component_from_lookup = _extract_component_from(extract_id=ExtractID(field="component_pk").from_lookup_kwargs)

_extract_hostprovider_from = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.PROVIDER,
    create_new=IDBasedAuditObjectCreator(model=HostProvider),
)
parent_hostprovider_from_lookup = _extract_hostprovider_from(
    extract_id=ExtractID(field="hostprovider_pk").from_lookup_kwargs
)

_extract_host_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.HOST, create_new=create_audit_host_object
)
host_from_lookup = _extract_host_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_host_from_lookup = _extract_host_from(extract_id=ExtractID(field="host_pk").from_lookup_kwargs)

_extract_user_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.USER, create_new=create_audit_user_object
)
user_from_response = _extract_user_from(extract_id=ExtractID(field="id").from_response)
user_from_lookup = _extract_user_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)


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
    if not new_name:
        return

    if instance.object_name == new_name:
        return

    instance.object_name = new_name
    instance.save(update_fields=["object_name"])


# hook helpers / special functions


def object_does_exist(hook: AuditHook, model: type[Model], id_field: str = "pk") -> bool:
    id_ = hook.call_arguments.get(id_field)
    if not id_:
        # it's quite a stretch, but I don't see an alternative way for a safe implementation here
        return False

    return model.objects.filter(id=id_).exists()


def nested_host_does_exist(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Host)


def retrieve_user_password_groups(id_: int) -> dict:
    if (user := User.objects.filter(pk=id_).first()) is None:
        return {}

    return {"password": user.password, "group": list(user.groups.values_list("name", flat=True).order_by("name"))}


# name changers


class set_add_hosts_name(AuditHook):  # noqa: N801
    def __call__(self):
        request = self.call_arguments.get("request", "")

        data = None
        # if body was already read without assigning to `request._data`,
        # those exceptions won't be enough to silence,
        # but if such a problem will occur, it should be addressed more thoughtfully than just suppress
        with suppress(AttributeError, json.JSONDecodeError):
            data = json.loads(request.body)

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


bundle_from_lookup = GeneralAuditObjectRetriever(
    audit_object_type=AuditObjectType.BUNDLE,
    create_new=IDBasedAuditObjectCreator(model=Bundle),
    extract_id=ExtractID(field="pk").from_lookup_kwargs,
)
