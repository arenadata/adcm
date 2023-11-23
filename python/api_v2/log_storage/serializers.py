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

# pylint: disable=duplicate-code
import json

from cm.ansible_plugin import get_checklogs_data_by_job_id
from cm.models import LogStorage
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from adcm import settings


class LogStorageSerializer(ModelSerializer):
    content = SerializerMethodField()

    class Meta:
        model = LogStorage
        fields = (
            "id",
            "name",
            "type",
            "format",
            "content",
        )

    @staticmethod
    def _get_ansible_content(obj):
        path_file = settings.RUN_DIR / f"{obj.job.id}" / f"{obj.name}-{obj.type}.{obj.format}"
        try:
            with open(path_file, encoding=settings.ENCODING_UTF_8) as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        return content

    def get_content(self, obj: LogStorage) -> str:
        if obj.type in {"stdout", "stderr"}:
            if obj.body is None:
                obj.body = self._get_ansible_content(obj)
        elif obj.type == "check":
            if obj.body is None:
                obj.body = get_checklogs_data_by_job_id(obj.job_id)
            if isinstance(obj.body, str):
                obj.body = json.loads(obj.body)
        elif obj.type == "custom":
            if obj.format == "json" and isinstance(obj.body, str):
                try:
                    custom_content = json.loads(obj.body)
                    obj.body = json.dumps(custom_content, indent=4)
                except json.JSONDecodeError:
                    pass

        return obj.body
