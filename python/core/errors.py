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

from contextlib import contextmanager

from core.types import ADCMComposableError, ADCMCoreError, ADCMMessageError


class NotFoundError(ADCMMessageError):
    ...


class ConfigValueError(ADCMCoreError):
    """
    Added as part of ADCM-6355.
    May be removed/reworked later.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg


@contextmanager
def localize_error(*locations: str):
    try:
        yield
    except ADCMComposableError as e:
        for location in reversed(locations):
            e.add_prefix(location)
        raise
