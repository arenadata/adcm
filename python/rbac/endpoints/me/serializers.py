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


from rbac.models import User
from rest_framework.serializers import CharField, ModelSerializer


class MeUserSerializer(ModelSerializer):
    password = CharField(trim_whitespace=False, required=False, write_only=True)
    current_password = CharField(trim_whitespace=False, required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "password",
            "current_password",
            "profile",
            "type",
            "is_active",
            "failed_login_attempts",
        )
        read_only_fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "type",
            "is_active",
            "failed_login_attempts",
        )
