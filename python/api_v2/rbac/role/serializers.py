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
from rest_framework.fields import BooleanField, CharField
from rest_framework.serializers import (
    ManyRelatedField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SlugRelatedField,
)


class RoleChildSerializer(ModelSerializer):
    is_built_in = BooleanField(source="built_in", default=False, read_only=True)
    is_any_category = BooleanField(source="any_category", default=False, read_only=True)
    categories = SlugRelatedField(read_only=True, many=True, slug_field="value", source="category")

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "display_name",
            "is_built_in",
            "is_any_category",
            "categories",
            "type",
        )
        extra_kwargs = {"name": {"read_only": True}, "type": {"read_only": True}}


class RoleSerializer(RoleChildSerializer):
    children = RoleChildSerializer(many=True, source="child", read_only=True)

    class Meta:
        model = Role
        fields = (
            *RoleChildSerializer.Meta.fields,
            "parametrized_by_type",
            "description",
            "children",
        )
        extra_kwargs = {"name": {"read_only": True}, "type": {"read_only": True}}


class RoleCreateSerializer(ModelSerializer):
    children = ManyRelatedField(child_relation=PrimaryKeyRelatedField(queryset=Role.objects.all()), source="child")
    name = CharField(max_length=1000, default="")

    class Meta:
        model = Role
        fields = ("name", "display_name", "description", "children")
        extra_kwargs = {"display_name": {"required": True}, "children": {"required": True}}


class RoleUpdateSerializer(ModelSerializer):
    children = ManyRelatedField(
        child_relation=PrimaryKeyRelatedField(queryset=Role.objects.all()), source="child", required=False
    )
    name = CharField(max_length=1000, required=False)

    class Meta:
        model = Role
        fields = ("name", "display_name", "description", "children")


class RoleRelatedSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "display_name"]
