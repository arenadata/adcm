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

from rest_framework import serializers
from rest_framework.reverse import reverse

from cm.models import ConfigLog, ObjectConfig


class VersionConfigLogURL(serializers.RelatedField):
    def to_representation(self, value):
        return reverse(
            viewname="config-log-detail",
            kwargs={"pk": value},
            request=self.context["request"],
            format=self.context["format"],
        )


class HistoryConfigLogURL(serializers.HyperlinkedRelatedField):
    view_name = "config-log-list"
    queryset = ConfigLog.objects.all()


class ObjectConfigSerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()
    current = VersionConfigLogURL(read_only=True)
    previous = VersionConfigLogURL(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="config-detail")

    class Meta:
        model = ObjectConfig
        fields = ("id", "history", "current", "previous", "url")

    def get_history(self, obj):
        url = reverse(
            viewname="config-log-list",
            request=self.context["request"],
            format=self.context["format"],
        )
        return f"{url}?obj_ref={obj.pk}&ordering=-id"
