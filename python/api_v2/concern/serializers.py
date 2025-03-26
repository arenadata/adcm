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

from typing import TypedDict

from adcm.serializers import EmptySerializer
from cm.models import ConcernItem
from cm.utils import get_obj_type
from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework.fields import CharField, DictField, SerializerMethodField
from rest_framework.serializers import BooleanField, ModelSerializer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Placeholder for flag of cluster",
            value={
                "message": "${source} has flag: outdated config",
                "placeholder": {"source": {"name": "Awesome", "type": "cluster", "params": {"cluster_id": 4}}},
            },
        )
    ]
)
class ReasonSerializer(EmptySerializer):
    message = CharField()
    placeholder = DictField()


class _ConcernOwner(TypedDict):
    id: int
    type: str | None


class ConcernSerializer(ModelSerializer):
    is_blocking = BooleanField(source="blocking")
    owner = SerializerMethodField()
    reason = ReasonSerializer()

    class Meta:
        model = ConcernItem
        fields = ("id", "type", "reason", "is_blocking", "cause", "owner")

    @extend_schema_field(_ConcernOwner)
    def get_owner(self, obj):
        return {
            "id": obj.owner_id,
            "type": get_obj_type(obj.owner_type.name) if obj.owner_type else None,
        }
