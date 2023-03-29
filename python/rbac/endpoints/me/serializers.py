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

from collections import OrderedDict

from cm.errors import raise_adcm_ex
from rbac.endpoints.fields import PasswordField
from rbac.models import User
from rest_framework.serializers import ModelSerializer


class MeUserSerializer(ModelSerializer):
    password = PasswordField(trim_whitespace=False, required=False)
    current_password = PasswordField(trim_whitespace=False, required=False)

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
        )

    def validate(self, attrs: OrderedDict) -> OrderedDict:
        if not attrs.get("password"):
            return attrs

        if self.instance.check_password(raw_password=attrs["password"]):
            return attrs

        if not (attrs.get("current_password") and self.instance.check_password(raw_password=attrs["current_password"])):
            raise_adcm_ex(code="USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR")

        attrs.pop("current_password")

        return attrs
