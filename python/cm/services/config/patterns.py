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

import re

from typing_extensions import Self


class Pattern:
    __slots__ = ("_pattern", "_compiled")

    def __init__(self, regex_pattern: str) -> None:
        self._pattern = regex_pattern
        self._compiled = None

    @property
    def raw(self) -> str:
        return self._pattern

    @property
    def compiled(self) -> re.Pattern:
        if self._compiled:
            return self._compiled

        self.compile()

        return self._compiled

    @property
    def is_valid(self) -> bool:
        try:
            self.compile()
            return True
        except re.error:
            return False

    def compile(self) -> Self:
        self._compiled = self._compiled or re.compile(self._pattern)
        return self

    def matches(self, value: str) -> bool:
        return bool(self.compiled.search(value))
