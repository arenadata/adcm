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

from rbac.models import Role
from rbac.utils import BaseRelatedSerializer
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.fields import RegexField, SerializerMethodField
from rest_framework.relations import HyperlinkedIdentityField, PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer


class RoleChildSerializer(BaseRelatedSerializer):
    id = PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = HyperlinkedIdentityField(view_name="rbac:role-detail")


class RoleSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    url = HyperlinkedIdentityField(view_name="rbac:role-detail")
    child = RoleChildSerializer(many=True)
    name = RegexField(r"^[^\n]*$", max_length=160, required=False, allow_blank=True)
    display_name = RegexField(r"^[^\n]*$", max_length=160, required=True)
    category = SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "description",
            "display_name",
            "built_in",
            "type",
            "category",
            "parametrized_by_type",
            "child",
            "url",
            "any_category",
        )
        extra_kwargs = {
            "parametrized_by_type": {"read_only": True},
            "built_in": {"read_only": True},
            "type": {"read_only": True},
            "any_category": {"read_only": True},
        }
        expandable_fields = {"child": ("rbac.endpoints.role.views.RoleSerializer", {"many": True})}

    @staticmethod
    def get_category(obj):
        return [c.value for c in obj.category.all()]


class RoleAuditSerializer(ModelSerializer):
    child = SerializerMethodField()

    class Meta:
        model = Role
        fields = ("name", "display_name", "description", "child")

    @staticmethod
    def get_child(obj: Role) -> list[str, ...]:
        return [role.display_name for role in obj.child.all()]
