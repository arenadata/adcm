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

from api_v2.rbac.group.serializers import GroupRelatedSerializer
from api_v2.rbac.role.serializers import RoleRelatedSerializer
from rbac.endpoints.policy.serializers import ObjectField
from rbac.models import Policy
from rest_framework.fields import BooleanField, IntegerField
from rest_framework.serializers import ModelSerializer

from adcm.serializers import EmptySerializer


class PolicySerializer(ModelSerializer):
    is_built_in = BooleanField(read_only=True, source="built_in")
    groups = GroupRelatedSerializer(many=True, source="group")
    objects = ObjectField(required=True, source="object")
    role = RoleRelatedSerializer(read_only=True)

    class Meta:
        model = Policy
        fields = [
            "id",
            "name",
            "description",
            "is_built_in",
            "objects",
            "groups",
            "role",
        ]


class PolicyRoleCreateSerializer(EmptySerializer):
    id = IntegerField()


class PolicyGroupCreateSerializer(EmptySerializer):
    id = IntegerField()


class PolicyObjectCreateSerializer(EmptySerializer):
    id = IntegerField()


class PolicyCreateSerializer(ModelSerializer):
    groups = PolicyGroupCreateSerializer(many=True, source="group")
    objects = ObjectField(required=True, source="object")
    role = PolicyRoleCreateSerializer()

    class Meta:
        model = Policy
        fields = [
            "id",
            "name",
            "description",
            "objects",
            "groups",
            "role",
        ]
