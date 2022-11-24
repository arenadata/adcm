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

"""Complex checks for audit tests stored here"""

from datetime import datetime
from pprint import pformat
from typing import Collection, List, NamedTuple, Tuple, Union

import allure
from adcm_client.audit import AuditLogin, AuditOperation, OperationResult
from adcm_client.objects import ADCMClient
from docker.models.containers import Container

DATETIME_FMT = "%Y-%m-%d %H:%M:%S.%f%z"

CEF_VERSION = "CEF: 0"
VENDOR = "Arenadata Software"
PRODUCT = "Arenadata Cluster Manager"


class CEFRecord(NamedTuple):
    """CEF log sections"""

    cef_version: str
    vendor: str
    product: str
    version: str
    signature_id: str
    name: str
    severity: str
    extension: str


# pylint: disable-next=too-many-locals
def check_audit_cef_logs(client: ADCMClient, adcm_container: Container):
    """
    Retrieve CEF logs from docker container output
    and check that they are the same (and in the same order) as audit log records from API
    """
    version = client.adcm_version
    operations = client.audit_operation_list(paging={"limit": 200})
    logins = client.audit_login_list()
    logs: List[Union[AuditOperation, AuditLogin]] = list(operations) + list(logins)
    logs.sort(
        key=lambda log_operation: log_operation.operation_time
        if isinstance(log_operation, AuditOperation)
        else log_operation.login_time
    )
    exit_code, out = adcm_container.exec_run(["cat", "/adcm/data/log/audit.log"])
    logfile_content = out.decode("utf-8")
    if exit_code != 0:
        raise ValueError(f"Failed to get audit logfile content: {logfile_content}")
    # filter out empty
    cef_records: Tuple[CEFRecord, ...] = tuple(
        map(
            lambda r: CEFRecord(*r.split("|")),
            filter(lambda log_operation: 'CEF' in log_operation, logfile_content.split("\n")),
        )
    )
    with allure.step("Check all logs have correct CEF version, vendor, product name and version"):
        for param, expected in (
            ("cef_version", CEF_VERSION),
            ("vendor", VENDOR),
            ("product", PRODUCT),
            ("version", version),
        ):
            if any(getattr(rec, param) != expected for rec in cef_records):
                _attach_cef_logs(cef_records)
                raise AssertionError(
                    f"Incorrect {param} in one of records.\nExpected: {expected}\nCheck attachments for more details"
                )
    with allure.step("Check that of audit logs (operations + logins) should be same as CEF logs"):
        if (audit_amount := len(logs)) != (cef_amount := len(cef_records)):
            _attach_api_logs(logs)
            raise AssertionError(f"Lengths are not the same.\nAudit logs: {audit_amount}.\nCEF logs: {cef_amount}")
    with allure.step(
        "Check that all audit logs (operations and logins) have corresponding CEF record in container logs"
    ):
        for i, log in enumerate(logs):
            result, name, extension = _extract_basic_info(client, log)
            with allure.step(f"Check CEF log #{i} is corresponding to {log.id} '{name}' with result '{result}'"):
                corresponding_cef_log: CEFRecord = cef_records[i]
                expected_severity = "3" if result == OperationResult.DENIED.value else "1"
                for param, expected in (
                    ("name", name),
                    ("severity", expected_severity),
                    ("extension", extension),
                ):

                    if getattr(corresponding_cef_log, param) != expected:
                        _attach_api_log(log)
                        _attach_cef_logs(cef_records)
                        raise AssertionError(
                            f"Incorrect {param}. Expected {param}: {expected}.\n"
                            f"Actual record:\n{pformat(corresponding_cef_log)}"
                        )


def _extract_basic_info(client: ADCMClient, log: Union[AuditOperation, AuditLogin]) -> Tuple[str, str, str]:
    """Return result, name and extension"""
    username = client.user(id=log.user_id).username if log.user_id else None
    if isinstance(log, AuditOperation):
        time = _format_time(log.operation_time)
        return (
            (result := log.operation_result.value),
            (name := log.operation_name),
            " ".join(
                f'{k}="{v}"'
                for k, v in {
                    'actor': username,
                    'act': log.operation_type.value,
                    'operation': name,
                    'resource': log.object_name,
                    'result': result,
                    'timestamp': time,
                }.items()
                if v is not None
            ),
        )
    time = _format_time(log.login_time)
    return (
        (result := log.login_result.value),
        (name := "User logged"),
        f'actor="{username}" operation="{name}" result="{result}" timestamp="{time}"',
    )


def _format_time(time: datetime):
    t = time.strftime(DATETIME_FMT)
    return f'{t[:-2]}:{t[-2:]}'


def _attach_cef_logs(cef_logs: Collection[CEFRecord]) -> None:
    allure.attach(
        pformat(cef_logs),
        name="Parsed CEF logs from container",
        attachment_type=allure.attachment_type.TEXT,
    )


def _attach_api_log(api_log: Union[AuditOperation, AuditLogin]) -> None:
    allure.attach(
        _prepare_log_for_attachment(api_log),
        name="Audit record",
        attachment_type=allure.attachment_type.TEXT,
    )


def _attach_api_logs(api_logs: Collection[Union[AuditOperation, AuditLogin]]) -> None:
    allure.attach(
        pformat([_prepare_log_for_attachment(log) for log in api_logs]),
        name="Audit records",
        attachment_type=allure.attachment_type.TEXT,
    )


def _prepare_log_for_attachment(api_log: Union[AuditOperation, AuditLogin]) -> str:
    fields = [f for f in dir(api_log) if not (not f.islower() or f.startswith("_") or callable(getattr(api_log, f)))]
    fields.pop(fields.index("adcm_version"))
    return pformat({k: getattr(api_log, k) for k in fields})
