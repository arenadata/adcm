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

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, NamedTuple, TypeVar

from cm.models import ADCM, ADCMEntity, Cluster, ClusterObject, Host, HostProvider, JobLog, Prototype, ServiceComponent

_PlaceholderObjectT = TypeVar("_PlaceholderObjectT", bound=Callable)


class PlaceholderObjectsDTO(NamedTuple):
    source: ADCMEntity | None = None
    target: ADCMEntity | Prototype | None = None
    job: JobLog | None = None


class PlaceholderTypeDTO(NamedTuple):
    source: str | None = None
    target: str | None = None


NO_TYPES_IN_PLACEHOLDERS = PlaceholderTypeDTO()


@dataclass(slots=True, frozen=True)
class Placeholder(Generic[_PlaceholderObjectT]):
    retrieve: Callable[[_PlaceholderObjectT], dict] | None = None

    @property
    def is_required(self) -> bool:
        return self.retrieve is not None


class Placeholders:
    source: Placeholder[ADCMEntity]
    target: Placeholder[ADCMEntity | Prototype]
    job: Placeholder[JobLog]

    def __init__(
        self,
        retrieve_source: Callable[[ADCMEntity], dict] | None = None,
        retrieve_target: Callable[[ADCMEntity | Prototype], dict] | None = None,
        retrieve_job: Callable[[JobLog], dict] | None = None,
    ):
        self.source = Placeholder(retrieve=retrieve_source)
        self.target = Placeholder(retrieve=retrieve_target)
        self.job = Placeholder(retrieve=retrieve_job)


@dataclass(frozen=True, slots=True)
class ConcernMessageTemplate:
    message: str
    placeholders: Placeholders


def _retrieve_placeholder_from_adcm_entity(
    entity: Cluster | ClusterObject | ServiceComponent | HostProvider | Host | ADCM,
) -> dict:
    return {
        "type": entity.prototype.type,
        "name": entity.display_name,
        "params": entity.get_id_chain(),
    }


def _retrieve_placeholder_from_prototype(entity: Prototype) -> dict:
    if not isinstance(entity, Prototype):
        message = f"Expected instance of Prototype, not {type(entity)}"
        raise TypeError(message)

    return {
        "params": {"prototype_id": entity.id},
        "type": "prototype",
        "name": entity.display_name or entity.name,
    }


def _retrieve_placeholder_from_job(entity: JobLog) -> dict:
    return {
        "type": "job",
        "name": entity.display_name or entity.name,
        # thou it's named `job_id` it is task_id, because UI uses it in that way for routing
        "params": {"task_id": entity.task_id},
    }


ADCM_ENTITY_AS_PLACEHOLDERS = Placeholders(retrieve_source=_retrieve_placeholder_from_adcm_entity)


class ConcernMessage(Enum):
    CONFIG_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with its config", placeholders=ADCM_ENTITY_AS_PLACEHOLDERS
    )
    HOST_COMPONENT_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with host-component mapping", placeholders=ADCM_ENTITY_AS_PLACEHOLDERS
    )
    REQUIRED_IMPORT_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with required import", placeholders=ADCM_ENTITY_AS_PLACEHOLDERS
    )
    REQUIRED_SERVICE_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with required service: ${target}",
        placeholders=Placeholders(
            retrieve_source=_retrieve_placeholder_from_adcm_entity, retrieve_target=_retrieve_placeholder_from_prototype
        ),
    )
    UNSATISFIED_REQUIREMENT_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with requirement. Need to be installed: ${target}",
        placeholders=Placeholders(
            retrieve_source=_retrieve_placeholder_from_adcm_entity, retrieve_target=_retrieve_placeholder_from_prototype
        ),
    )
    LOCKED_BY_JOB = ConcernMessageTemplate(
        message="Object was locked by running job ${job} on ${target}",
        placeholders=Placeholders(
            retrieve_job=_retrieve_placeholder_from_job,
            retrieve_target=_retrieve_placeholder_from_adcm_entity,
        ),
    )
    # Note that flag's message in template is just "left part"
    # and should be combined with actual flag's message
    FLAG = ConcernMessageTemplate(message="${source} has a flag: ", placeholders=ADCM_ENTITY_AS_PLACEHOLDERS)

    def __init__(self, template: ConcernMessageTemplate):
        self.template: ConcernMessageTemplate = template


def build_concern_reason(
    template: ConcernMessageTemplate,
    placeholder_objects: PlaceholderObjectsDTO,
    placeholder_types: PlaceholderTypeDTO = NO_TYPES_IN_PLACEHOLDERS,
) -> dict:
    resolved_placeholders = {}
    for placeholder_name in ("source", "target", "job"):
        placeholder: Placeholder = getattr(template.placeholders, placeholder_name)
        if not placeholder.is_required:
            continue

        entity = getattr(placeholder_objects, placeholder_name)
        if entity is None:
            # if there will be cases when those can be null, set placeholder to `{}` instead of error
            # check out commit history for more info
            message = f"Concern message '{template.message}' requires `{placeholder_name}` to fill placeholders"
            raise RuntimeError(message)

        resolved_placeholders[placeholder_name] = placeholder.retrieve(entity)

        if placeholder_type := getattr(placeholder_types, placeholder_name, None):
            resolved_placeholders[placeholder_name]["type"] = placeholder_type

    return {"message": template.message, "placeholder": resolved_placeholders}
