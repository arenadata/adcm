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

from core.action import TaskOwner
from core.action.job import JobUpdateDTO
from core.config import ConfigCoreObjectWithPrototype, RelatedConfigs
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, PrototypeID

from cm.impl.job.repo import JobRepo
from cm.legacy.services.config import retrieve_primary_configs
from cm.legacy.services.hierarchy import retrieve_object_hierarchy
from cm.models import JobLog


def create_related_configs(job_id: int, owner: TaskOwner) -> None:
    object_ = CoreObjectDescriptor(id=owner.id, type=owner.type)

    if owner.type in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT):
        # ADCM-6770
        # Please note that the service and components may be deleted while the task is running.
        # That is, the task container is deleted during its execution, and after deletion,
        # the task must be executed and successfully interact with other objects.
        cluster = owner.related_objects.cluster

        if cluster is None:
            raise RuntimeError(f"Cluster missing for {owner}")

        object_ = CoreObjectDescriptor(id=cluster.id, type=cluster.type)

    hierarchy = retrieve_object_hierarchy(object_=object_)
    related_configs = retrieve_primary_configs(objects=hierarchy)

    JobRepo().update_job(id=job_id, data=JobUpdateDTO(objects_related_configs=related_configs))


def get_new_related_configs(
    job_id: int, target: ConfigCoreObjectWithPrototype, new_config_id: ConfigID
) -> list[RelatedConfigs]:
    # The list cannot be empty, as it is prepared at the start, and if the job has been started,
    # then at least one object must be in the hierarchy. If this is not the case,
    # we believe that this is a mistake, and we want to know about it explicitly.
    related_configs: list[RelatedConfigs] = JobLog.objects.values_list("objects_related_configs", flat=True).get(
        id=job_id
    )
    related_configs: dict[CoreObjectDescriptor, tuple[PrototypeID, ConfigID]] = {
        CoreObjectDescriptor(id=cfg["object_id"], type=cfg["object_type"]): (
            cfg["prototype_id"],
            cfg["primary_config_id"],
        )
        for cfg in related_configs
    }

    # Parallel modification of the same `target`'s config should not cause errors,
    # since `objects_related_configs` stores snapshots of hierarchy configs on job start
    # Known case: multiple non-blocking service install actions, modifying the same cluster's config
    prototype_id, _ = related_configs[target.object]
    related_configs[target.object] = (prototype_id, new_config_id)

    return [
        RelatedConfigs(object_id=cod.id, object_type=cod.type, prototype_id=ids[0], primary_config_id=ids[1])
        for cod, ids in related_configs.items()
    ]


def update_related_configs(
    job_id: int, object_: CoreObjectDescriptor, object_prototype_id: int, old_config_id: int, new_config_id: int
) -> None:
    target_config = ConfigCoreObjectWithPrototype(
        object=object_,
        prototype_id=object_prototype_id,
        config_id=old_config_id,
    )
    related_configs = get_new_related_configs(job_id=job_id, target=target_config, new_config_id=new_config_id)
    JobRepo().update_job(id=job_id, data=JobUpdateDTO(objects_related_configs=related_configs))
