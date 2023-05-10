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


from audit.cases.adcm import adcm_case
from audit.cases.cluster import cluster_case
from audit.cases.common import action_case, task_job_case, upgrade_case
from audit.cases.config import config_case
from audit.cases.host_and_provider import host_and_provider_case
from audit.cases.rbac import rbac_case
from audit.cases.service import service_case
from audit.cases.stack import stack_case
from audit.models import AuditObject, AuditOperation
from django.db.models import Model
from django.views import View
from rest_framework.response import Response


def get_audit_operation_and_object(
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation | None, AuditObject | None, str | None]:
    operation_name = None
    path = view.request.path.replace("/api/v1/", "")[:-1].split("/")

    # Order of if elif is important, do not change it please
    if "action" in path:
        audit_operation, audit_object = action_case(path=path)
    elif "upgrade" in path:
        audit_operation, audit_object = upgrade_case(path=path)
    elif "stack" in path:
        audit_operation, audit_object = stack_case(
            path=path,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif (
        "cluster" in path  # pylint: disable=too-many-boolean-expressions
        or "component" in path
        or ("host" in path and "config" in path)
        or ("service" in path and "import" in path)
        or ("service" in path and "config" in path)
    ):
        audit_operation, audit_object = cluster_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "rbac" in path:
        audit_operation, audit_object = rbac_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "group-config" in path or "config-log" in path:
        audit_operation, audit_object, operation_name = config_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "host" in path or "provider" in path:
        audit_operation, audit_object = host_and_provider_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "service" in path:
        audit_operation, audit_object = service_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "adcm" in path:
        audit_operation, audit_object = adcm_case(path=path)
    elif "task" in path or "job" in path:
        audit_operation, audit_object = task_job_case(path=path)
    else:
        return None, None, None

    if not operation_name and audit_operation:
        operation_name = audit_operation.name

    return audit_operation, audit_object, operation_name
