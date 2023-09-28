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
from typing import Dict

from api_v2.bundle.serializers import BundleIdSerializer
from api_v2.prototype.utils import get_license_text
from cm.models import Prototype
from rest_framework.fields import CharField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from adcm.serializers import EmptySerializer


class PrototypeListSerializer(ModelSerializer):
    license = SerializerMethodField()
    bundle = BundleIdSerializer(read_only=True)

    class Meta:
        model = Prototype
        fields = (
            "id",
            "name",
            "display_name",
            "description",
            "type",
            "bundle",
            "license",
            "version",
        )

    def get_license(self, obj: Prototype) -> Dict:
        return {"status": obj.license, "text": get_license_text(obj)}


class PrototypeVersionSerializer(ModelSerializer):
    id = IntegerField(source="pk")
    version = CharField()
    bundle = BundleIdSerializer(read_only=True)
    license_status = CharField(source="license")

    class Meta:
        model = Prototype
        fields = ("id", "bundle", "version", "license_status")


class PrototypeTypeSerializer(EmptySerializer):
    name = CharField()
    display_name = CharField()
    versions = SerializerMethodField()

    @staticmethod
    def get_versions(obj: Prototype) -> str | None:
        queryset = Prototype.objects.filter(type=obj.type, name=obj.name).order_by("-version")
        serializer = PrototypeVersionSerializer(instance=queryset, many=True)

        return serializer.data


class PrototypeRelatedSerializer(ModelSerializer):
    class Meta:
        model = Prototype
        fields = ("id", "name", "display_name", "type", "version")
