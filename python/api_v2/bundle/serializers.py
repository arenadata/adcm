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

from cm.models import Bundle
from rest_framework.fields import DateTimeField, FileField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from adcm.serializers import EmptySerializer


class BundleListSerializer(ModelSerializer):
    display_name = SerializerMethodField()
    upload_time = DateTimeField(read_only=True, source="date")

    class Meta:
        model = Bundle
        fields = ("id", "name", "display_name", "version", "edition", "upload_time", "category")

    def get_display_name(self, instance) -> str | None:
        prototype = instance.prototype_set.filter(type__in=["adcm", "cluster", "provider"]).first()
        return prototype.display_name


class UploadBundleSerializer(EmptySerializer):
    file = FileField(help_text="bundle file for upload")
