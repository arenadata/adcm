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

from django.db.models import Model
from django.views import View
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from audit.cases.adcm import adcm_case
from audit.cases.bundle import bundle_case
from audit.cases.cluster import cluster_case
from audit.cases.common import action_case, task_job_case, upgrade_case
from audit.cases.config import config_case
from audit.cases.host import host_case
from audit.cases.license import license_case
from audit.cases.provider import provider_case
from audit.cases.rbac import rbac_case
from audit.cases.service import service_case
from audit.cases.stack import stack_case
from audit.models import AuditObject, AuditOperation


def get_audit_operation_and_object(
    view: View | GenericAPIView,
    response: Response | None,
    deleted_obj: Model,
    path: list[str],
    api_version: int = 1,
) -> tuple[AuditOperation | None, AuditObject | None, str | None]:
    operation_name = None

    # Order of if elif is important, do not change it please
    if "action" in path or "actions" in path:
        audit_operation, audit_object = action_case(path=path, api_version=api_version)
    elif "upgrade" in path or "upgrades" in path:
        audit_operation, audit_object = upgrade_case(path=path)
    elif "stack" in path:
        audit_operation, audit_object = stack_case(
            path=path,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif (
        "cluster" in path
        or ("clusters" in path and "config-groups" not in path)
        or "component" in path
        or ("host" in path and "config" in path)
        or ("service" in path and ("import" in path or "config" in path))
        or "ansible-config" in path
    ):
        audit_operation, audit_object = cluster_case(
            path=path, view=view, response=response, deleted_obj=deleted_obj, api_version=api_version
        )
    elif "rbac" in path:
        audit_operation, audit_object = rbac_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "group-config" in path or "config-log" in path or "config-groups" in path:
        audit_operation, audit_object, operation_name = config_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "host" in path or "hosts" in path:
        audit_operation, audit_object = host_case(
            path=path,
            view=view,
            response=response,
            deleted_obj=deleted_obj,
        )
    elif "provider" in path or "hostproviders" in path:
        audit_operation, audit_object = provider_case(
            path=path,
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
    elif "adcm" in path or "profile" in path:
        audit_operation, audit_object = adcm_case(path=path, view=view, response=response, api_version=api_version)
    elif "task" in path or "tasks" in path or "job" in path or "jobs" in path:
        audit_operation, audit_object = task_job_case(path=path, version=api_version)
    elif "bundles" in path:
        audit_operation, audit_object = bundle_case(
            path=path,
            view=view,
            deleted_obj=deleted_obj,
        )
    elif "accept" in path:
        audit_operation, audit_object = license_case(path=path, view=view, response=response)
    else:
        return None, None, None

    if not operation_name and audit_operation:
        operation_name = audit_operation.name

    return audit_operation, audit_object, operation_name
