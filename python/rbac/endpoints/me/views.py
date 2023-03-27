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

from rbac import models
from rbac.services import user as user_services
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.serializers import BooleanField, CharField, IntegerField, JSONField

from adcm.serializers import EmptySerializer


class PasswordField(CharField):
    """Text field with content masking for passwords"""

    def to_representation(self, value):
        return user_services.PW_MASK


class MeUserSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    username = CharField(read_only=True)
    first_name = CharField(read_only=True)
    last_name = CharField(read_only=True)
    email = CharField(read_only=True)
    is_superuser = BooleanField(read_only=True)
    password = PasswordField(trim_whitespace=False)
    profile = JSONField(required=False, default="")
    type = CharField(read_only=True)
    is_active = BooleanField(read_only=True)

    def update(self, instance, validated_data):
        context_user = self.context["request"].user

        return user_services.update(instance, context_user, partial=True, **validated_data)


class MyselfView(RetrieveUpdateAPIView):
    queryset = models.User.objects.all()
    serializer_class = MeUserSerializer

    def get_object(self):
        # request user object is disconnected from DB, use another instance
        user = models.User.objects.get(id=self.request.user.id)

        return user
