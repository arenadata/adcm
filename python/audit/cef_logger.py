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


from collections import OrderedDict
import logging

from django.conf import settings

from audit.apps import AuditConfig
from audit.models import AuditLog, AuditLogOperationResult, AuditSession

audit_logger = logging.getLogger(AuditConfig.name)


class CEFLogConstants:
    cef_version: str = "CEF: 0"
    device_vendor: str = "Arenadata Software"
    device_product: str = "Arenadata Cluster Manager"
    adcm_version: str = settings.ADCM_VERSION
    operation_name_session: str = "User logged"
    extension_keys: tuple[str, ...] = (
        "actor",
        "act",
        "operation",
        "resource",
        "result",
        "timestamp",
        "address",
        "agent",
    )


def cef_logger(
    audit_instance: AuditLog | AuditSession,
    signature_id: str,
    severity: int = 1,
    empty_resource: bool = False,
) -> None:
    extension = OrderedDict.fromkeys(CEFLogConstants.extension_keys, None)

    if isinstance(audit_instance, AuditSession):
        operation_name = CEFLogConstants.operation_name_session
        if audit_instance.user is not None:
            extension["actor"] = audit_instance.user.username
        elif audit_instance.login_details.get("username"):
            extension["actor"] = audit_instance.login_details["username"]
        extension["operation"] = operation_name
        extension["result"] = audit_instance.login_result
        extension["timestamp"] = str(audit_instance.login_time)
        extension["address"] = audit_instance.address
        extension["agent"] = audit_instance.agent

    elif isinstance(audit_instance, AuditLog):
        operation_name = audit_instance.operation_name
        if audit_instance.user is not None:
            extension["actor"] = audit_instance.user.username
        extension["act"] = audit_instance.operation_type
        extension["operation"] = operation_name
        if not empty_resource and audit_instance.audit_object:
            extension["resource"] = audit_instance.audit_object.object_name
        extension["result"] = audit_instance.operation_result
        if audit_instance.operation_result == AuditLogOperationResult.DENIED:
            severity = 3
        extension["timestamp"] = str(audit_instance.operation_time)
        extension["address"] = audit_instance.address
        extension["agent"] = audit_instance.agent

    else:
        raise NotImplementedError

    extension = " ".join([f'{k}="{v}"' for k, v in extension.items() if v is not None])

    msg = (
        f"{CEFLogConstants.cef_version}|{CEFLogConstants.device_vendor}|"
        f"{CEFLogConstants.device_product}|{CEFLogConstants.adcm_version}|"
        f"{signature_id}|{operation_name}|{severity}|{extension}"
    )

    audit_logger.info(msg)
