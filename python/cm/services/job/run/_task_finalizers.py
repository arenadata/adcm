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

from logging import Logger
from typing import Protocol

from core.cluster.types import HostComponentEntry
from core.job.types import Task
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings

from cm.converters import core_type_to_model
from cm.issue import unlock_affected_objects, update_hierarchy_issues
from cm.models import (
    ActionHostGroup,
    JobLog,
    MaintenanceMode,
    TaskLog,
    get_object_cluster,
)
from cm.services.concern.messages import ConcernMessage, PlaceholderObjectsDTO, build_concern_reason
from cm.services.mapping import change_host_component_mapping, check_nothing
from cm.status_api import send_object_update_event

# todo "unwrap" these functions to use repo without directly calling ORM,
#  try to rework functions like `save_hc` also, because they rely on API v1 input
#  which is in no way correct approach


class WithIDAndCoreType(Protocol):
    id: int
    type: ADCMCoreType


def set_job_lock(job_id: int) -> None:
    job = JobLog.objects.select_related("task").get(pk=job_id)
    object_ = job.task.task_object
    if isinstance(object_, ActionHostGroup):
        object_ = object_.object

    if job.task.lock and object_:
        job.task.lock.reason = build_concern_reason(
            ConcernMessage.LOCKED_BY_JOB.template,
            placeholder_objects=PlaceholderObjectsDTO(job=job, target=object_),
        )
        job.task.lock.save(update_fields=["reason"])


def set_hostcomponent(task: Task, logger: Logger):
    task_object = TaskLog.objects.prefetch_related("task_object").get(id=task.id).task_object

    cluster = get_object_cluster(task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task.id)

        return

    logger.warning("task #%s is failed, restore old hc", task.id)

    change_host_component_mapping(
        cluster_id=cluster.id,
        bundle_id=cluster.prototype.bundle_id,
        flat_mapping=(
            HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
            for entry in task.hostcomponent.saved
        ),
        checks_func=check_nothing,
    )


def remove_task_lock(task_id: int) -> None:
    unlock_affected_objects(TaskLog.objects.get(pk=task_id))


def update_issues(object_: CoreObjectDescriptor):
    update_hierarchy_issues(obj=core_type_to_model(core_type=object_.type).objects.get(id=object_.id))


def update_object_maintenance_mode(action_name: str, object_: WithIDAndCoreType):
    """
    If maintenance mode wasn't changed during action execution, set "opposite" (to action's name) MM
    """
    obj = core_type_to_model(core_type=object_.type).objects.get(id=object_.id)

    if (
        action_name in {settings.ADCM_TURN_ON_MM_ACTION_NAME, settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.OFF
        obj.save()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})

    if (
        action_name in {settings.ADCM_TURN_OFF_MM_ACTION_NAME, settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.ON
        obj.save()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})
