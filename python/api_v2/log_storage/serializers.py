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
from contextlib import suppress

from cm.ansible_plugin import get_checklogs_data_by_job_id
from cm.models import LogStorage
from django.conf import settings
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer


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

    def get_content(self, obj: LogStorage) -> str:
        content = obj.body
        log_type = obj.type

        # retrieve if empty
        if content is None:
            if log_type in {"stdout", "stderr"}:
                logfile = settings.RUN_DIR / f"{obj.job_id}" / f"{obj.name}-{obj.type}.{obj.format}"
                if logfile.exists():
                    content = logfile.read_text(encoding="utf-8")

            if log_type == "check":
                content = get_checklogs_data_by_job_id(obj.job_id)

        # postprocessing
        if log_type in {"stdout", "stderr"} and len(content or "") >= settings.STDOUT_STDERR_LOG_MAX_UNCUT_LENGTH:
            cut_lines = "\n".join(
                (
                    line
                    if len(line) <= settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH
                    else (
                        line[: settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH]
                        + settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE
                    )
                    for line in obj.body.splitlines()[-1500:]
                )
            )
            content = f"{settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE}\n{cut_lines}\n"
        elif log_type == "check" and isinstance(content, str):
            content = json.loads(obj.body)
        elif log_type == "custom" and obj.format == "json" and isinstance(content, str):
            with suppress(json.JSONDecodeError):
                custom_content = json.loads(content)
                content = json.dumps(custom_content)

        return content or ""
