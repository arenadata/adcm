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

from api.concern.serializers import ConcernItemSerializer
from api.serializers import StringListSerializer
from cm.adcm_config import get_main_info
from cm.models import ADCM
from rest_framework.serializers import (
    CharField,
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    SerializerMethodField,
)


class ADCMSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = ADCM
        fields = ("id", "name", "state", "prototype_id", "url")
        extra_kwargs = {"url": {"lookup_url_kwarg": "adcm_pk"}}


class ADCMRetrieveSerializer(HyperlinkedModelSerializer):
    prototype_version = CharField(
        read_only=True,
        source="prototype.version",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    action = HyperlinkedIdentityField(view_name="object-action", lookup_url_kwarg="adcm_pk")
    config = HyperlinkedIdentityField(view_name="object-config", lookup_url_kwarg="adcm_pk")

    class Meta:
        model = ADCM
        fields = (
            "id",
            "name",
            "prototype_id",
            "bundle_id",
            "state",
            "locked",
            "prototype_version",
            "multi_state",
            "concerns",
            "action",
            "config",
            "url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "adcm_pk"}}


class ADCMUISerializer(HyperlinkedModelSerializer):
    prototype_version = CharField(
        read_only=True,
        source="prototype.version",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    action = HyperlinkedIdentityField(view_name="object-action", lookup_url_kwarg="adcm_pk")
    config = HyperlinkedIdentityField(view_name="object-config", lookup_url_kwarg="adcm_pk")
    main_info = SerializerMethodField()

    class Meta:
        model = ADCM
        fields = (
            "id",
            "name",
            "prototype_id",
            "bundle_id",
            "state",
            "locked",
            "prototype_version",
            "multi_state",
            "concerns",
            "action",
            "config",
            "main_info",
            "url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "adcm_pk"}}

    @staticmethod
    def get_main_info(obj):
        return get_main_info(obj)
