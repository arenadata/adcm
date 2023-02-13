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

from api.utils import get_api_url_kwargs, hlink
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    IntegerField,
    JSONField,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class ConcernItemSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    url = hlink("concern-details", "id", "concern_id")


class ConcernItemUISerializer(ConcernItemSerializer):
    type = CharField()
    blocking = BooleanField()
    reason = JSONField()
    cause = CharField()


class ConcernItemDetailSerializer(ConcernItemUISerializer):
    name = CharField()
    related_objects = SerializerMethodField()
    owner = SerializerMethodField()

    def get_related_objects(self, item):
        result = []
        for obj in item.related_objects:
            view_name = f"{obj.prototype.type}-details"
            request = self.context.get("request", None)
            kwargs = get_api_url_kwargs(obj, request, no_obj_type=True)
            result.append(
                {
                    "type": obj.prototype.type,
                    "id": obj.pk,
                    "url": reverse(view_name, kwargs=kwargs, request=request),
                }
            )
        return result

    def get_owner(self, item):
        request = self.context.get("request", None)
        kwargs = get_api_url_kwargs(item.owner, request, no_obj_type=True)
        return {
            "type": item.owner.prototype.type,
            "id": item.owner.pk,
            "url": reverse(f"{item.owner.prototype.type}-details", kwargs=kwargs, request=request),
        }
