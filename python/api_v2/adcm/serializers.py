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
from rest_framework.serializers import BooleanField, CharField, ModelSerializer

from adcm.serializers import EmptySerializer


class LoginSerializer(EmptySerializer):
    username = CharField(write_only=True)
    password = CharField(style={"input_type": "password"}, trim_whitespace=False, write_only=True)


class ProfileSerializer(ModelSerializer):
    new_password = CharField(trim_whitespace=False, required=False, write_only=True, source="password")
    current_password = CharField(trim_whitespace=False, required=False, write_only=True)
    is_super_user = BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_super_user",
            "new_password",
            "current_password",
        ]
        read_only_fields = ["username", "email", "first_name", "last_name", "is_super_user"]
