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

from dataclasses import dataclass
from typing import Callable, Protocol

from rest_framework.response import Response

from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result
from audit.models import AuditObject, AuditObjectType


def ignore_object_search(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Response | None,
    exception: Exception | None,
) -> AuditObject | None:
    """Do not attempt to search for object (e.g. object will be deleted after request is finished)"""
    _ = call_arguments, result, exception

    return context.object


class ExtractAuditObjectIDFunc(Protocol):
    def __call__(self, call_arguments: AuditedCallArguments, result: Result | None) -> str | int | None:
        ...


@dataclass(slots=True)
class GeneralAuditObjectRetriever:
    """
    Unification of object retrieval process:
    1. Try to get id
    2. Try to retrieve audit object by this ID and audit object type
    3. On retrieval fail, call create function (it is expected to return Audit Object if it can be created)
    """

    audit_object_type: AuditObjectType

    extract_id: ExtractAuditObjectIDFunc
    create_new: Callable[[str, AuditObjectType], AuditObject | None]

    is_deleted: bool = False

    def __call__(
        self,
        context: "OperationAuditContext",  # noqa: ARG002
        call_arguments: AuditedCallArguments,
        result: Result | None,
        exception: Exception | None,  # noqa: ARG002
    ) -> AuditObject | None:
        id_ = self.extract_id(call_arguments=call_arguments, result=result)
        if not id_:
            return None

        audit_object = AuditObject.objects.filter(
            object_id=id_, object_type=self.audit_object_type, is_deleted=self.is_deleted
        ).first()
        if audit_object:
            return audit_object

        return self.create_new(id_, self.audit_object_type)
