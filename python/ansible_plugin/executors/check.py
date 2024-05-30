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

from typing import Collection, TypedDict

from cm.errors import AdcmEx
from cm.logger import logger
from cm.models import CheckLog, GroupCheckLog, JobLog, LogStorage
from core.types import CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import BaseModel, model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.errors import (
    PluginRuntimeError,
)
from ansible_plugin.utils import assign_view_logstorage_permissions_by_job


class CheckArguments(BaseModel):
    title: str
    result: bool
    msg: str | None = None
    fail_msg: str | None = None
    success_msg: str | None = None
    group_title: str | None = None
    group_success_msg: str | None = None
    group_fail_msg: str | None = None

    @model_validator(mode="after")
    def check_msg_is_specified_if_no_fail_success_msg(self) -> Self:
        if self.success_msg is None and self.fail_msg is None and self.msg is None:
            message = "'msg' must be specified if 'success_msg' and 'fail_msg' are not specified"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_success_msg_and_fail_msg_are_specified_if_no_msg(self) -> Self:
        if self.msg:
            return self

        if self.success_msg is None or self.fail_msg is None:
            message = "Both success_msg and fail_msg should be specified when msg is absent"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_group_msg_if_group_is_specified(self) -> Self:
        if (
            self.group_title is not None
            and self.group_success_msg is None
            and self.group_title is not None
            and self.group_fail_msg is None
        ):
            message = "either 'group_fail_msg' or 'group_success_msg' must be specified if 'group_titile' is specified"
            raise ValueError(message)

        return self


class JSONLogReturnValue(TypedDict):
    check: dict


class ADCMCheckPluginExecutor(ADCMAnsiblePluginExecutor[CheckArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=CheckArguments),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: CallArguments, runtime: RuntimeEnvironment
    ) -> CallResult[None]:
        _ = targets, runtime

        if arguments.success_msg and arguments.result:
            msg = arguments.success_msg
        elif not arguments.success_msg and arguments.result:
            msg = arguments.msg
        elif arguments.fail_msg:
            msg = arguments.fail_msg
        else:
            msg = arguments.msg

        group_data = {
            "title": arguments.group_title,
            "success_msg": arguments.group_success_msg,
            "fail_msg": arguments.group_fail_msg,
        }

        check_data = {
            "title": arguments.title.replace("\x00", ""),
            "result": arguments.result,
            "message": msg.replace("\x00", ""),
        }

        logger.debug(
            "ansible adcm_check: %s, %s",
            ", ".join([f"{k}: {v}" for k, v in group_data.items() if v]),
            ", ".join([f"{k}: {v}" for k, v in check_data.items() if v]),
        )

        try:
            with atomic():
                job = JobLog.objects.get(id=runtime.vars.job.id)
                group_title = group_data.pop("title")

                if group_title:
                    group, _ = GroupCheckLog.objects.get_or_create(job=job, title=group_title)
                else:
                    group = None

                check_data.update({"job": job, "group": group})
                CheckLog.objects.create(**check_data)

                if group is not None:
                    group_data.update({"group": group})
                    logs = CheckLog.objects.filter(group=group).values("result")
                    result = all(log["result"] for log in logs)

                    msg = group_data["success_msg"] if result else group_data["fail_msg"]

                    group.message = msg
                    group.result = result
                    group.save(update_fields=["message", "result"])

                log_storage, _ = LogStorage.objects.get_or_create(job=job, name="ansible", type="check", format="json")

                assign_view_logstorage_permissions_by_job(log_storage)
        except AdcmEx as e:
            error_message = f"Failed to create checklog: {check_data}, group: {group_data}, error: {e}"
            return CallResult(value=None, changed=False, error=PluginRuntimeError(message=error_message))

        return CallResult(value=None, changed=True, error=None)
