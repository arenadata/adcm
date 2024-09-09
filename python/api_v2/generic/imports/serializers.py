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

from adcm.serializers import EmptySerializer
from cm.models import Cluster, ObjectType
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import BooleanField, CharField, ChoiceField, IntegerField, SerializerMethodField

from api_v2.cluster.serializers import ClusterStatusSerializer


class SourceSerializer(EmptySerializer):
    id = IntegerField()
    type = ChoiceField(choices=[ObjectType.CLUSTER, ObjectType.SERVICE])


class ImportPostSerializer(EmptySerializer):
    source = SourceSerializer()


class UIPrototypeSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    display_name = CharField()
    version = CharField()


class UIImportClusterSerializer(EmptySerializer):
    id = IntegerField()
    is_multi_bind = BooleanField()
    is_required = BooleanField()
    prototype = UIPrototypeSerializer()


class UIIMportServicesSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    display_name = CharField()
    version = CharField()
    is_required = BooleanField()
    is_multi_bind = BooleanField()
    prototype = UIPrototypeSerializer()


class UIBindSourceSerializer(EmptySerializer):
    id = IntegerField()
    type = ChoiceField(choices=[ObjectType.CLUSTER, ObjectType.SERVICE])


class UIBindSerializer(EmptySerializer):
    id = IntegerField()
    source = UIBindSourceSerializer()


class ImportSerializer(EmptySerializer):
    import_cluster = UIImportClusterSerializer(many=False)
    import_services = UIIMportServicesSerializer(many=True)
    binds = UIBindSerializer(many=True)

    cluster = SerializerMethodField()

    @staticmethod
    @extend_schema_field(field=ClusterStatusSerializer)
    def get_cluster(obj: Cluster) -> dict | None:
        return ClusterStatusSerializer(instance=obj).data
