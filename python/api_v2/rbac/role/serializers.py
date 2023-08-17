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
from rest_framework.fields import BooleanField, CharField, SerializerMethodField
from rest_framework.serializers import ModelSerializer


class RoleChildSerializer(ModelSerializer):
    is_built_in = BooleanField(source="built_in", default=False)
    is_any_category = BooleanField(source="any_category", default=False)
    categories = SerializerMethodField(read_only=True)
    name = CharField(max_length=1000, default="", source="category")

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

    @staticmethod
    def get_categories(obj) -> list:
        if hasattr(obj, "category"):
            return [c.value for c in obj.category.all()]
        return []


class RoleSerializer(RoleChildSerializer):
    children = RoleChildSerializer(many=True, source="child")
    name = CharField(max_length=1000)

    class Meta:
        model = Role
        fields = (
            *RoleChildSerializer.Meta.fields,
            "description",
            "children",
        )
