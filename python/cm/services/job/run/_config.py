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

from core.config.types import ConfigCoreObjectWithPrototype, RelatedConfigs
from core.job.dto import JobUpdateDTO
from core.job.types import TaskOwner
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor

from cm.models import JobLog
from cm.services.config import retrieve_primary_configs
from cm.services.hierarchy import retrieve_object_hierarchy
from cm.services.job.run.repo import JobRepoImpl


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

    JobRepoImpl.update_job(id=job_id, data=JobUpdateDTO(objects_related_configs=related_configs))


def get_new_related_configs(
    job_id: int, target: ConfigCoreObjectWithPrototype, new_config_id: ConfigID
) -> list[RelatedConfigs]:
    related_configs: list[RelatedConfigs] = JobLog.objects.values_list("objects_related_configs", flat=True).get(
        id=job_id
    )

    # The list cannot be empty, as it is prepared at the start, and if the job has been started,
    # then at least one object must be in the hierarchy. If this is not the case,
    # we believe that this is a mistake, and we want to know about it explicitly.

    target_config = RelatedConfigs(
        object_id=target.object.id,
        object_type=target.object.type.value,
        prototype_id=target.prototype_id,
        primary_config_id=target.config_id,
    )
    index = related_configs.index(target_config)
    record = related_configs[index]
    record["primary_config_id"] = new_config_id

    return related_configs


def update_related_configs(
    job_id: int, object_: CoreObjectDescriptor, object_prototype_id: int, old_config_id: int, new_config_id: int
) -> None:
    target_config = ConfigCoreObjectWithPrototype(
        object=object_,
        prototype_id=object_prototype_id,
        config_id=old_config_id,
    )
    related_configs = get_new_related_configs(job_id=job_id, target=target_config, new_config_id=new_config_id)
    JobRepoImpl.update_job(id=job_id, data=JobUpdateDTO(objects_related_configs=related_configs))
