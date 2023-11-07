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
from api_v2.prototype.utils import get_license_text
from cm.models import Bundle, HostProvider, ObjectType, Prototype
from rest_framework.fields import DateTimeField, FileField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from adcm.serializers import EmptySerializer


class BundleRelatedSerializer(ModelSerializer):
    class Meta:
        model = Bundle
        fields = ["id", "edition"]


class BundleListSerializer(ModelSerializer):
    upload_time = DateTimeField(read_only=True, source="date")
    display_name = SerializerMethodField()

    class Meta:
        model = Bundle
        fields = ("id", "name", "display_name", "version", "edition", "upload_time", "category", "signature_status")

    @staticmethod
    def get_display_name(bundle: Bundle) -> str:
        proto = bundle.prototype_set.filter(type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER]).first()
        return proto.display_name


class UploadBundleSerializer(EmptySerializer):
    file = FileField(help_text="bundle file for upload")


class UpgradeServicePrototypeSerializer(ModelSerializer):
    license = SerializerMethodField()

    class Meta:
        model = Prototype
        fields = ("id", "name", "display_name", "version", "license")

    @staticmethod
    def get_license(prototype: Prototype) -> dict:
        return {"status": prototype.license, "text": get_license_text(prototype=prototype)}


class UpgradeBundleSerializer(ModelSerializer):
    prototype_id = SerializerMethodField()
    license_status = SerializerMethodField()
    unaccepted_services_prototypes = SerializerMethodField()

    class Meta:
        model = Bundle
        fields = ["id", "prototype_id", "license_status", "unaccepted_services_prototypes"]

    def get_prototype_id(self, bundle: Bundle) -> int:
        return bundle.prototype_set.filter(type__in=(ObjectType.CLUSTER, ObjectType.PROVIDER)).first().pk

    def get_license_status(self, bundle: Bundle) -> str:
        return bundle.prototype_set.filter(type__in=(ObjectType.CLUSTER, ObjectType.PROVIDER)).first().license

    def get_unaccepted_services_prototypes(self, bundle: Bundle) -> list:
        if isinstance(self.context["parent"], HostProvider):
            return []

        added_services = self.context["parent"].clusterobject_set.all().values_list("prototype__name", flat=True)
        prototypes = bundle.prototype_set.filter(
            type=ObjectType.SERVICE, license="unaccepted", name__in=added_services
        ).order_by("pk")

        return UpgradeServicePrototypeSerializer(instance=prototypes, many=True).data
