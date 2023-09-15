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

from cm.errors import AdcmEx
from rbac.models import User


def unblock_user(user: User) -> None:
    if user.built_in:
        raise AdcmEx(code="USER_BLOCK_ERROR")

    user.failed_login_attempts = 0
    user.blocked_at = None
    user.save(update_fields=["failed_login_attempts", "blocked_at"])
