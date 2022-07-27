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

"""Management utility to create superusers"""

from django.contrib.auth.management.commands.createsuperuser import (
    Command as AuthCommand,
)
from rbac.models import User


class Command(AuthCommand):
    """Redefined createsuperuser command with replaced User model"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = User
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)
