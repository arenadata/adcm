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

from audit.cases.common import obj_pk_case
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)


def adcm_case(path: list[str, ...]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (["adcm", adcm_pk, "config", "history"] | ["adcm", adcm_pk, "config", "history", _, "restore"]):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.ADCM,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=adcm_pk,
                operation_aux_str="configuration ",
            )

    return audit_operation, audit_object
