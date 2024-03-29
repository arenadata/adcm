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

from cm.models import ADCMEntity, JobLog, Prototype

_PlaceholderObjectT = TypeVar("_PlaceholderObjectT", bound=Callable)


class PlaceholderObjectsDTO(NamedTuple):
    source: ADCMEntity | None = None
    target: ADCMEntity | Prototype | None = None
    job: JobLog | None = None


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


def _retrieve_placeholder_from_adcm_entity(entity: ADCMEntity) -> dict:
    return {
        "type": entity.prototype.type,
        "name": entity.display_name,  # fixme only entities with display name can be here, not any ADCMEntity
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
    # todo should be updated after task rework feature branch is merged
    #  name should be taken from `entity.task.display_name`
    action = entity.sub_action or entity.action

    return {
        "type": "job",
        "name": action.display_name or action.name,
        # todo should it be job id or task id?
        "params": {"job_id": entity.task.id},
    }


ADCM_ENTITY_SOURCE_RESOLVER = Placeholders(retrieve_source=_retrieve_placeholder_from_adcm_entity)


class ConcernMessage(Enum):
    CONFIG_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with its config", placeholders=ADCM_ENTITY_SOURCE_RESOLVER
    )
    HOST_COMPONENT_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with host-component mapping", placeholders=ADCM_ENTITY_SOURCE_RESOLVER
    )
    REQUIRED_IMPORT_ISSUE = ConcernMessageTemplate(
        message="${source} has an issue with required import", placeholders=ADCM_ENTITY_SOURCE_RESOLVER
    )
    REQUIRED_SERVICE_ISSUE = ConcernMessageTemplate(
        message="${source} require service ${target} to be installed",
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
    # todo update message and naming here
    FLAG = ConcernMessageTemplate(
        message="${source} has an outdated configuration", placeholders=ADCM_ENTITY_SOURCE_RESOLVER
    )

    def __init__(self, template: ConcernMessageTemplate):
        self.template = template


def build_concern_reason(concern_message: ConcernMessage, placeholder_objects: PlaceholderObjectsDTO) -> dict:
    template = concern_message.template

    resolved_placeholders = {}
    for placeholder_name in ("source", "target", "job"):
        placeholder: Placeholder = getattr(template.placeholders, placeholder_name)
        if not placeholder.is_required:
            continue

        entity = getattr(placeholder_objects, placeholder_name)
        if entity is None:
            # todo if there will be cases when those can be null, set placeholder to `{}` instead of error
            message = f"Concern message {concern_message.name} requires `{placeholder_name}` to fill placeholders"
            raise RuntimeError(message)

        resolved_placeholders[placeholder_name] = placeholder.retrieve(entity)

    return {"message": template.message, "placeholder": resolved_placeholders}
