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
from operator import itemgetter

from core.job.types import Task
from core.types import CoreObjectDescriptor
from django.conf import settings

from cm.api import save_hc
from cm.converters import core_type_to_model
from cm.issue import unlock_affected_objects, update_hierarchy_issues
from cm.models import ClusterObject, Host, JobLog, MaintenanceMode, ServiceComponent, TaskLog, get_object_cluster

# todo "unwrap" these functions to use repo without directly calling ORM,
#  try to rework functions like `save_hc` also, because they rely on API v1 input
#  which is in no way correct approach


def set_job_lock(job_id: int) -> None:
    job = JobLog.objects.select_related("task").get(pk=job_id)
    if job.task.lock and job.task.task_object:
        job.task.lock.reason = job.cook_reason()
        job.task.lock.save(update_fields=["reason"])


def set_hostcomponent(task: Task, logger: Logger):
    task_object = TaskLog.objects.prefetch_related("task_object").get(id=task.id).task_object

    cluster = get_object_cluster(task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task.id)

        return

    new_hostcomponent = task.hostcomponent.saved
    hosts = {
        entry.pk: entry for entry in Host.objects.filter(id__in=set(map(itemgetter("host_id"), new_hostcomponent)))
    }
    services = {
        entry.pk: entry
        for entry in ClusterObject.objects.filter(id__in=set(map(itemgetter("service_id"), new_hostcomponent)))
    }
    components = {
        entry.pk: entry
        for entry in ServiceComponent.objects.filter(id__in=set(map(itemgetter("component_id"), new_hostcomponent)))
    }

    host_comp_list = [
        (services[entry["service_id"]], hosts[entry["host_id"]], components[entry["component_id"]])
        for entry in new_hostcomponent
    ]

    logger.warning("task #%s is failed, restore old hc", task.id)

    save_hc(cluster, host_comp_list)


def remove_task_lock(task_id: int) -> None:
    unlock_affected_objects(TaskLog.objects.get(pk=task_id))


def update_issues(object_: CoreObjectDescriptor):
    update_hierarchy_issues(obj=core_type_to_model(core_type=object_.type).objects.get(id=object_.id))


def update_object_maintenance_mode(action_name: str, object_: CoreObjectDescriptor):
    obj = core_type_to_model(core_type=object_.type).objects.get(id=object_.id)

    if (
        action_name in {settings.ADCM_TURN_ON_MM_ACTION_NAME, settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.OFF
        obj.save()

    if (
        action_name in {settings.ADCM_TURN_OFF_MM_ACTION_NAME, settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.ON
        obj.save()
