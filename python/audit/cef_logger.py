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


import json
import logging
from collections import OrderedDict
from typing import Optional, Tuple, Union

from django.utils import timezone as tz

from audit.apps import AuditConfig
from audit.models import AuditLog, AuditLogOperationResult, AuditSession


audit_log = logging.getLogger(AuditConfig.name)

TEMPLATE = (
    '{syslog_header}'
    '{cef_version}|{device_vendor}|{device_product}|'
    '{adcm_version}|{signature_id}|{name}|{severity}|{extension}'
)


def get_adcm_version():
    with open('/adcm/config.json', encoding='utf-8') as f:
        return json.loads(f.read())['version']


class CEFLogConstants:
    syslog_header: str = ''
    cef_version: str = 'CEF: 0'
    device_vendor: str = 'Arenadata Software'
    device_product: str = 'Arenadata Cluster Manager'
    adcm_version: str = get_adcm_version()
    severity: int = 1
    operation_name_session: str = 'User logged'
    extension_keys: Tuple[str] = ('actor', 'act', 'operation', 'resource', 'result', 'timestamp')


def cef_log(
    audit_instance: Union[AuditLog, AuditSession],
    signature_id: str,
    severity: Optional[int] = None,
    empty_resource: bool = False,
) -> None:
    extension = OrderedDict.fromkeys(CEFLogConstants.extension_keys, None)
    extension['timestamp'] = str(tz.now())

    if isinstance(audit_instance, AuditSession):
        operation_name = CEFLogConstants.operation_name_session
        if audit_instance.user:
            extension['actor'] = audit_instance.user.username
        else:
            extension['actor'] = audit_instance.login_details.get('username', '<undefined>')
        extension['operation'] = operation_name
        extension['result'] = audit_instance.login_result

    elif isinstance(audit_instance, AuditLog):
        operation_name = audit_instance.operation_name
        extension['actor'] = audit_instance.user.username
        extension['act'] = audit_instance.operation_type
        extension['operation'] = operation_name
        if not empty_resource and audit_instance.audit_object:
            extension['resource'] = audit_instance.audit_object.object_name
        extension['result'] = audit_instance.operation_result
        if audit_instance.operation_result == AuditLogOperationResult.Denied:
            severity = 3

    else:
        raise NotImplementedError

    msg = TEMPLATE.format(
        syslog_header=CEFLogConstants.syslog_header,
        cef_version=CEFLogConstants.cef_version,
        device_vendor=CEFLogConstants.device_vendor,
        device_product=CEFLogConstants.device_product,
        adcm_version=CEFLogConstants.adcm_version,
        signature_id=signature_id,
        name=operation_name,
        severity=severity if severity is not None else CEFLogConstants.severity,
        extension=' '.join([f'{k}={v}' for k, v in extension.items() if v is not None]),
    )
    audit_log.info(msg)
