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

from collections.abc import Collection
from typing import Annotated, TypedDict

from cm.errors import AdcmEx
from core.logs import CheckLogArguments, GroupCheckLogArguments, Severity
from core.types import CoreObjectDescriptor
from pydantic import AfterValidator, model_validator
from typing_extensions import Self
from use_cases.logs.check import AddCheckLogRecordForJob

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.errors import (
    PluginRuntimeError,
)


def _clean(s: str | None) -> str | None:
    if s is None:
        return s

    return s.replace("\x00", "")


clean_symbols = AfterValidator(_clean)
CleanOptionalString = Annotated[str | None, clean_symbols]
CleanString = Annotated[str, clean_symbols]


class CheckArguments(BaseStrictModel):
    title: CleanString
    result: bool
    msg: CleanOptionalString = None
    fail_msg: CleanOptionalString = None
    success_msg: CleanOptionalString = None
    group_title: CleanOptionalString = None
    group_success_msg: CleanString = ""
    group_fail_msg: CleanString = ""
    severity: Severity = Severity.ERROR

    @model_validator(mode="after")
    def check_msg_is_specified_if_no_fail_success_msg(self) -> Self:
        if self.success_msg is None and self.fail_msg is None and self.msg is None:
            message = "'msg' must be specified if 'success_msg' and 'fail_msg' are not specified"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_success_msg_and_fail_msg_are_specified_if_no_msg(self) -> Self:
        if self.msg is not None:
            return self

        if self.success_msg is None or self.fail_msg is None:
            message = "Both success_msg and fail_msg should be specified when msg is absent"
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

        group = None

        if arguments.group_title:
            group = GroupCheckLogArguments(
                title=arguments.group_title,
                success_msg=arguments.group_success_msg,
                fail_msg=arguments.group_fail_msg,
            )

        dto = CheckLogArguments(
            title=arguments.title,
            result=arguments.result,
            success_msg=arguments.success_msg if arguments.success_msg else arguments.msg,
            fail_msg=arguments.fail_msg if arguments.fail_msg else arguments.msg,
            severity=arguments.severity,
            group=group,
        )

        try:
            add_check_log_record = self._container.get(AddCheckLogRecordForJob)
            add_check_log_record.do(job_id=runtime.vars.job.id, check_log_arguments=dto)
        except AdcmEx as e:
            error_message = f"Failed to create checklog: {dto}, error: {e}"
            return CallResult(value="", changed=False, error=PluginRuntimeError(message=error_message))

        return CallResult(value="", changed=True, error=None)
