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

from pydantic import ValidationError


class ADCMPluginError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class PluginRuntimeError(ADCMPluginError):
    ...


class PluginTargetError(ADCMPluginError):
    ...


class PluginTargetDetectionError(PluginTargetError):
    ...


class PluginValidationError(ADCMPluginError):
    ...


class PluginContextError(ADCMPluginError):
    ...


class PluginIncorrectCallError(ADCMPluginError):
    ...


def compose_validation_error_details_message(err: ValidationError) -> str:
    return "\n".join(f"\t{'.'.join(error['loc'])} - {error['msg']}" for error in err.errors())
