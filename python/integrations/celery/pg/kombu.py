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

from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import dataclass
from datetime import datetime
import json

from django.db import connection

# Exclude service queues with the '.pidbox' suffix.
LIST_MESSAGES_QUERY = """
    SELECT m.visible, m."timestamp", m.payload
    FROM kombu_message AS m
    JOIN kombu_queue AS q ON q.id = m.queue_id
    WHERE q.name NOT LIKE '%.pidbox'
"""


class KombuMessageDecodeError(ValueError):
    """A Kombu message cannot be decoded as a Celery JSON message."""


@dataclass(frozen=True, slots=True, kw_only=True)
class MessagePayload:
    # Celery ids can be UUID strings or custom string ids
    celery_task_id: str | None = None
    adcm_task_id: int | None = None
    adcm_job_id: int | None = None


@dataclass(frozen=True, slots=True)
class TaskMessageSnapshot(MessagePayload):
    visible: bool
    timestamp: datetime | None
    error: KombuMessageDecodeError | None = None


def list_messages() -> list[TaskMessageSnapshot]:
    """Read both visible and claimed messages, excluding service queues."""
    with connection.cursor() as cursor:
        cursor.execute(LIST_MESSAGES_QUERY)
        rows = cursor.fetchall()

    messages: list[TaskMessageSnapshot] = []
    for is_visible, timestamp, payload in rows:
        try:
            parsed_payload = _parse_payload(payload)
        except KombuMessageDecodeError as error:
            messages.append(TaskMessageSnapshot(visible=is_visible, timestamp=timestamp, error=error))
            continue
        messages.append(
            TaskMessageSnapshot(
                visible=is_visible,
                timestamp=timestamp,
                celery_task_id=parsed_payload.celery_task_id,
                adcm_task_id=parsed_payload.adcm_task_id,
                adcm_job_id=parsed_payload.adcm_job_id,
            )
        )
    return messages


def _parse_payload(payload: str) -> MessagePayload:
    celery_task_id = None
    try:
        message = json.loads(payload)
        headers = message.get("headers") or {}
        celery_task_id = headers.get("id")
        decoded = b64decode(message["body"], validate=True).decode("utf-8")
        body = json.loads(decoded)
        kwargs = body[1]
        return MessagePayload(
            celery_task_id=celery_task_id,
            adcm_task_id=kwargs.get("task_id"),
            adcm_job_id=kwargs.get("job_id"),
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, UnicodeError, Base64Error) as error:
        task_id_info = celery_task_id if celery_task_id is not None else "undefined"
        raise KombuMessageDecodeError(
            f"Failed to parse JSON payload; celery_task_id={task_id_info}: {error}"
        ) from error
