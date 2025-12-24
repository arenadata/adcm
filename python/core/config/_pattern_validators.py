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

from dataclasses import dataclass

from core.config._pattern import Pattern
from core.config._secrets import AnsibleSecrets
from core.config._validate import PatternValidator


class PlainValuePatternValidator(PatternValidator):
    __slots__ = ()

    def is_match(self, value: str, pattern: str) -> bool:
        pattern_validator = Pattern(regex_pattern=pattern)
        return pattern_validator.matches(value)


@dataclass(slots=True)
class PossiblyEncryptedPatternValidator(PatternValidator):
    secrets: AnsibleSecrets

    def is_match(self, value: str, pattern: str) -> bool:
        decrypted = self.secrets.decrypt(value) or ""
        pattern_validator = Pattern(regex_pattern=pattern)
        return pattern_validator.matches(decrypted)
