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

from operator import itemgetter

from adcm.serializers import EmptySerializer
from cm.models import ActionHostGroup
from rest_framework.fields import CharField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer


class ShortHostSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()


class AddHostSerializer(EmptySerializer):
    host_id = IntegerField()


class ActionHostGroupCreateSerializer(EmptySerializer):
    name = CharField(max_length=150)
    description = CharField(max_length=255, allow_blank=True)


class ActionHostGroupSerializer(ModelSerializer):
    id = IntegerField()
    name = CharField(max_length=150)
    description = CharField(max_length=255)
    hosts = SerializerMethodField()

    def get_hosts(self, group: ActionHostGroup) -> list:
        # NOTE:
        #   Here we return "unpaginated" list of hosts, so if there will be lots of them, there may be problems with:
        #     - sorting here instead of DB (use `Prefetch` object with order)
        #     - prefetching WHOLE hosts, when the only thing we require is "id" and "name" ("fqdn" field in DB)
        #     - prefetching ALL hosts (this one will require API changes => impossible to solve at this level)
        #
        #   See implementation of `ActionHostGroupViewSet` for more details
        return sorted(ShortHostSerializer(instance=group.hosts.all(), many=True).data, key=itemgetter("name"))

    class Meta:
        model = ActionHostGroup
        fields = ("id", "name", "description", "hosts")


class ActionHostGroupCreateResultSerializer(ActionHostGroupSerializer):
    def get_hosts(self, _: ActionHostGroup) -> list:
        return []
