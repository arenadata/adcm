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
from cm.models import LICENSE_STATE, Prototype
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import CharField, ChoiceField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from api_v2.bundle.serializers import BundleRelatedSerializer
from api_v2.prototype.utils import get_license_text
from api_v2.serializers import LicenseDict


class PrototypeSerializer(ModelSerializer):
    license = SerializerMethodField()
    bundle = BundleRelatedSerializer()

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

    @staticmethod
    @extend_schema_field(field=LicenseDict)
    def get_license(prototype: Prototype) -> dict:
        return {
            "status": prototype.license,
            "text": get_license_text(
                license_path=prototype.license_path,
                bundle_hash=prototype.bundle.hash,
            ),
        }


class PrototypeVersionSerializer(ModelSerializer):
    id = IntegerField(source="pk")
    version = CharField()
    bundle = BundleRelatedSerializer(read_only=True)
    license_status = ChoiceField(source="license", choices=LICENSE_STATE)

    class Meta:
        model = Prototype
        fields = ("id", "bundle", "version", "license_status")


class PrototypeVersionsSerializer(EmptySerializer):
    name = CharField()
    display_name = CharField()
    versions = SerializerMethodField()

    @staticmethod
    @extend_schema_field(field=PrototypeVersionSerializer(many=True))
    def get_versions(obj: Prototype) -> str | None:
        queryset = (
            Prototype.objects.select_related("bundle")
            .filter(type=obj.type, name=obj.name)
            .order_by("-version", "-bundle__edition")
        )
        serializer = PrototypeVersionSerializer(instance=queryset, many=True)

        return serializer.data


class PrototypeRelatedSerializer(ModelSerializer):
    class Meta:
        model = Prototype
        fields = ("id", "name", "display_name", "version")
