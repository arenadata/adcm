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

from contextlib import suppress
from enum import Enum
from pathlib import Path
from typing import Protocol
import json

from adcm.serializers import EmptySerializer
from cm.models import LogStorage
from core.logs import LogFormat, Severity
from django.conf import settings
from drf_spectacular.utils import PolymorphicProxySerializer
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import BooleanField, CharField, ChoiceField, IntegerField, ModelSerializer


class CheckLogContentType(str, Enum):
    CHECK = "check"
    GROUP = "group"


class StreamLogContentType(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    CUSTOM = "custom"


class BaseCheckLogContent(EmptySerializer):
    title = CharField()
    message = CharField()
    result = BooleanField()
    severity = ChoiceField(choices=[e.value for e in Severity])


class CheckLogContentSerializer(BaseCheckLogContent):
    type = ChoiceField(
        choices=[
            CheckLogContentType.CHECK.value,
        ]
    )


class GroupCheckLogContentSerializer(BaseCheckLogContent):
    type = ChoiceField(
        choices=[
            CheckLogContentType.GROUP.value,
        ]
    )
    content = CheckLogContentSerializer(many=True)


class CheckLogStorageSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    type = ChoiceField(
        choices=[
            CheckLogContentType.CHECK.value,
        ]
    )
    format = ChoiceField(choices=[LogFormat.JSON.value])
    content = PolymorphicProxySerializer(
        component_name="StorageCheckLogContent",
        serializers=[GroupCheckLogContentSerializer, CheckLogContentSerializer],
        resource_type_field_name=None,
        many=True,
    )


class StreamLogStorageSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    type = ChoiceField(choices=[e.value for e in StreamLogContentType])
    format = ChoiceField(choices=[e.value for e in LogFormat])
    content = CharField()


proxy_serializer = PolymorphicProxySerializer(
    component_name="StorageLogContent",
    serializers=[CheckLogStorageSerializer, StreamLogStorageSerializer],
    resource_type_field_name=None,
    many=True,
)


class LogStorageSerializer(ModelSerializer):
    content = SerializerMethodField()

    def get_content(self, obj: LogStorage) -> str | list[dict]:
        content = obj.body
        log_type = obj.type

        # retrieve if empty
        if content is None:
            if log_type in {"stdout", "stderr"}:
                content = extract_log_content_from_fs(jobs_dir=settings.RUN_DIR, log_info=obj)

            if log_type == "check":
                content = self.context["retrieve_check_logs_content_for_job"](job_id=obj.job_id)

        # postprocessing
        if (
            log_type in {"stdout", "stderr"}
            and content is not None
            and len(content) >= settings.STDOUT_STDERR_LOG_MAX_UNCUT_LENGTH
        ):
            cut_lines = "\n".join(
                line
                if len(line) <= settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH
                else (line[: settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH] + settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE)
                for line in content.splitlines()[-1500:]
            )
            content = (
                f"{settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE}\n"
                f"{cut_lines}\n"
                f"{settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE}\n"
            )
        elif log_type == "check" and isinstance(content, str):
            content = json.loads(content)
        elif log_type == "custom" and obj.format == "json" and isinstance(content, str):
            with suppress(json.JSONDecodeError):
                custom_content = json.loads(content)
                content = json.dumps(custom_content)
        return content or ""

    class Meta:
        model = LogStorage
        fields = (
            "id",
            "name",
            "type",
            "format",
            "content",
        )


class BasicLogInfo(Protocol):
    job_id: int
    name: str
    type: str
    format: str


def extract_log_content_from_fs(jobs_dir: Path, log_info: BasicLogInfo) -> str | None:
    logfile = jobs_dir / f"{log_info.job_id}" / f"{log_info.name}-{log_info.type}.{log_info.format}"
    if logfile.exists():
        return logfile.read_text(encoding="utf-8")

    return None
