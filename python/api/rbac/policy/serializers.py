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

from cm.models import Cluster, Component, Host, Provider, Service
from cm.utils import get_obj_type
from rbac.models import Group, Policy, Role, RoleTypes
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.exceptions import ValidationError
from rest_framework.fields import (
    BooleanField,
    JSONField,
    RegexField,
    SerializerMethodField,
)
from rest_framework.relations import HyperlinkedIdentityField, PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer
import jsonschema

from api.rbac.serializers import BaseRelatedSerializer


class ObjectField(JSONField):
    @staticmethod
    def schema_validate(value):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "type": {
                        "type": "string",
                        "pattern": "^(cluster|service|component|provider|host)$",
                    },
                    "name": {
                        "type": "string",
                    },
                },
                "additionalProperties": True,
                "required": ["id", "type"],
            },
        }

        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError as e:
            raise ValidationError("the field does not match the scheme") from e

        return value

    def to_internal_value(self, data):
        self.schema_validate(data)
        dictionary = {
            "cluster": Cluster,
            "service": Service,
            "component": Component,
            "provider": Provider,
            "host": Host,
        }

        objects = []
        for obj in data:
            objects.append(dictionary[obj["type"]].obj.get(id=obj["id"]))

        return objects

    def to_representation(self, value):
        data = []
        for obj in value.all():
            data.append(
                {
                    "id": obj.object_id,
                    "type": obj.object.prototype.type,
                    "name": obj.object.display_name,
                },
            )

        return super().to_representation(data)


class PolicyRoleSerializer(BaseRelatedSerializer):
    id = PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = HyperlinkedIdentityField(view_name="v1:rbac:role-detail")


class PolicyGroupSerializer(BaseRelatedSerializer):
    id = PrimaryKeyRelatedField(queryset=Group.objects.all())
    url = HyperlinkedIdentityField(view_name="v1:rbac:group-detail")


class PolicySerializer(FlexFieldsSerializerMixin, ModelSerializer):
    url = HyperlinkedIdentityField(view_name="v1:rbac:policy-detail")
    name = RegexField(r"^[^\n]*$", max_length=160)
    object = ObjectField(required=True)
    built_in = BooleanField(read_only=True)
    role = PolicyRoleSerializer()
    group = PolicyGroupSerializer(many=True, required=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "description",
            "object",
            "built_in",
            "role",
            "group",
            "url",
        )
        expandable_fields = {
            "group": ("rbac.group.views.GroupSerializer", {"many": True}),
            "role": "rbac.role.views.RoleSerializer",
        }

    @staticmethod
    def validate_role(role):
        if role.type != RoleTypes.ROLE:
            raise ValidationError(f'Role with type "{role.type}" could not be used in policy')

        return role


class PolicyAuditSerializer(ModelSerializer):
    role = SerializerMethodField()
    object = SerializerMethodField()
    group = SerializerMethodField()

    class Meta:
        model = Policy
        fields = (
            "name",
            "description",
            "role",
            "object",
            "group",
        )

    @staticmethod
    def get_role(obj: Policy) -> str:
        if obj.role:
            return obj.role.display_name

        return ""

    @staticmethod
    def get_object(obj: Policy) -> list[dict[str, int | str]]:
        return [
            {
                "id": obj.object.pk,
                "name": obj.object.name,
                "type": get_obj_type(obj.content_type.name),
            }
            for obj in obj.object.all()
        ]

    @staticmethod
    def get_group(obj: Policy) -> list[str, ...]:
        return [group.name for group in obj.group.all()]
