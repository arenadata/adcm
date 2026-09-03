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

from core.types import CoreObjectDescriptor, ObjectID
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from cm.converters import CoreObject, core_type_to_model
from cm.legacy.services.concern.messages import ConcernMessage, PlaceholderObjectsDTO, build_concern_reason
from cm.models import (
    ADCM,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    JobLog,
    Provider,
    Service,
    TaskLog,
)


def get_lock_on_object(object_: Cluster | Service | Component | Provider | Host) -> ConcernItem | None:
    return object_.concerns.filter(type=ConcernType.LOCK).first()


def retrieve_lock_on_object(object_: CoreObjectDescriptor) -> ConcernItem | None:
    object_model = core_type_to_model(core_type=object_.type)
    id_field = f"{object_model.__name__.lower()}_id"

    related_locks_qs = object_model.concerns.through.objects.filter(
        concernitem__type=ConcernType.LOCK, **{id_field: object_.id}
    ).values_list("concernitem_id", flat=True)

    return ConcernItem.objects.filter(id__in=related_locks_qs).first()


def update_task_lock_concern(job_id: ObjectID) -> None:
    job = JobLog.objects.select_related("task").get(id=job_id)
    concern_id = job.task.lock_id
    if not concern_id:
        return

    owner = _get_task_owner(job.task)
    if owner is None:
        return

    # it's not nessesary to re-build reason,
    # but it's the most correct course for current implementation
    updated_reason = _build_lock_reason(job=job, owner=owner)
    ConcernItem.objects.filter(id=concern_id).update(reason=updated_reason)


def update_task_flag_concern(job_id: ObjectID) -> None:
    job = JobLog.objects.select_related("task").annotate(action_name=F("task__action__name")).get(id=job_id)
    owner = _get_task_owner(job.task)
    if owner is None:
        return

    concern = _detect_task_flag(owner=owner, action_name=job.action_name)
    if not concern:
        return

    concern.reason = _build_flag_reason(job=job, owner=owner)
    concern.save(update_fields=["reason"])


def delete_task_lock_concern(task_id: ObjectID) -> None:
    concern_id = TaskLog.objects.filter(id=task_id).values_list("lock_id", flat=True).first()
    if not concern_id:
        return

    ConcernItem.objects.filter(id=concern_id).delete()


def delete_task_flag_concern(task_id: ObjectID) -> None:
    task = TaskLog.objects.annotate(action_name=F("action__name")).filter(id=task_id).first()
    if not task:
        return

    owner = _get_task_owner(task)
    if not owner:
        return

    concern = _detect_task_flag(owner=owner, action_name=task.action_name)
    if not concern:
        return

    concern.delete()


def _detect_name_for_flag(action_name: str) -> str:
    return f"adcm_running_job_{action_name}"


def _build_lock_reason(job: JobLog, owner: CoreObject | ADCM) -> dict:
    return build_concern_reason(
        ConcernMessage.LOCKED_BY_JOB.template, placeholder_objects=PlaceholderObjectsDTO(job=job, target=owner)
    )


def _build_flag_reason(job: JobLog, owner: CoreObject | ADCM) -> dict:
    return build_concern_reason(
        ConcernMessage.FLAGGED_BY_JOB.template, placeholder_objects=PlaceholderObjectsDTO(job=job, source=owner)
    )


def _detect_task_flag(owner: CoreObject | ADCM, action_name: str) -> ConcernItem | None:
    name = _detect_name_for_flag(action_name)
    return ConcernItem.objects.filter(
        type=ConcernType.FLAG,
        cause=ConcernCause.JOB,
        name=name,
        owner_id=owner.pk,
        owner_type=ContentType.objects.get_for_model(owner),
    ).first()


def _get_task_owner(task: TaskLog) -> CoreObject | ADCM | None:
    """
    Get object that will have concerns to query
    """

    object_ = task.task_object
    if isinstance(object_, ActionHostGroup):
        return object_.object

    return object_
