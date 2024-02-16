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

from operator import attrgetter
from typing import Collection

from core.rbac.errors import ChangeMembershipError, PasswordError
from core.rbac.types import GroupBasicInfo, GroupID, PasswordRequirements, SourceType


def check_password_meet_requirements(password: str, requirements: PasswordRequirements) -> None:
    password_length = len(password)
    if password_length < requirements.min_length or password_length > requirements.max_length:
        message = (
            f"Your password can’t be shorter than {requirements.min_length} or longer than {requirements.max_length}."
        )
        raise PasswordError(message=message)


def check_add_user_to_groups_is_allowed(groups: Collection[GroupBasicInfo]) -> None:
    ldap_group = next((group for group in groups if group.type == SourceType.LDAP), None)
    if ldap_group:
        message = "You cannot add user to LDAP group"
        raise ChangeMembershipError(message)


def check_remove_user_from_groups_is_allowed(groups: Collection[GroupBasicInfo]) -> None:
    ldap_group = next((group for group in groups if group.type == SourceType.LDAP), None)
    if ldap_group:
        message = "You cannot remove user from original LDAP group"
        raise ChangeMembershipError(message)


def check_all_groups_exists(group_candidates: Collection[GroupID], existing_groups: Collection[GroupBasicInfo]):
    if not set(group_candidates).issubset(set(map(attrgetter("id"), existing_groups))):
        message = "Some of groups doesn't exist"
        raise ChangeMembershipError(message)
