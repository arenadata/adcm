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

from core.config._spec.parameters import ReadOnlyRule, WritableRule


def is_read_only(rule: ReadOnlyRule | WritableRule, owner_state: str) -> bool:
    match rule:
        case ReadOnlyRule(read_only="any"):
            return True

        case ReadOnlyRule(read_only=states):
            return owner_state in states

        case WritableRule(writable="any"):
            return False

        case WritableRule(writable=states):
            return owner_state not in states
