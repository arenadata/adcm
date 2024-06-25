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

from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result
from audit.alt.hooks import AuditHook
from audit.alt.object_retrievers import GeneralAuditObjectRetriever
from audit.models import AuditObject, AuditObjectType
from cm.models import Cluster, Host
from django.db.models import Model
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
class CMAuditObjectCreator:
    cm_model: type[Model]
    name_field: str = "name"

    def __call__(self, id_: str | int, audit_object_type: AuditObjectType) -> AuditObject | None:
        name = self.get_name(id_=id_)
        if not name:
            return None

        return AuditObject.objects.create(object_id=id_, object_type=audit_object_type, object_name=name)

    def get_name(self, id_: str | int) -> str | None:
        return self.cm_model.objects.values_list(self.name_field, flat=True).filter(id=id_).first()


create_audit_cluster_object = CMAuditObjectCreator(cm_model=Cluster)
create_audit_host_object = CMAuditObjectCreator(cm_model=Host, name_field="fqdn")

_extract_cluster_from = partial(
    GeneralAuditObjectRetriever, audit_object_type=AuditObjectType.CLUSTER, create_new=create_audit_cluster_object
)
cluster_from_response = _extract_cluster_from(extract_id=ExtractID(field="id").from_response)
cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_cluster_from_lookup = _extract_cluster_from(extract_id=ExtractID(field="cluster_pk").from_lookup_kwargs)

host_from_lookup = GeneralAuditObjectRetriever(
    audit_object_type=AuditObjectType.HOST,
    extract_id=ExtractID(field="pk").from_lookup_kwargs,
    create_new=create_audit_host_object,
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


# hook helpers / special functions


def object_does_exist(hook: AuditHook, model: type[Model], id_field: str = "pk") -> bool:
    id_ = hook.call_arguments.get(id_field)
    if not id_:
        # it's quite a stretch, but I don't see an alternative way for a safe implementation here
        return False

    return model.objects.filter(id=id_).exists()


def nested_host_does_exist(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Host)


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
