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
from typing import Any

from core.bundle_alt.schema import ActionProcessStep
from core.templates import RendererEnv, Template, get_renderer
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor

from cm.converters import core_type_to_model
from cm.services.jinja_env import get_env_for_jinja_config
from cm.services.job.run.repo import ActionRepoImpl
from cm.services.wizard import repo
from cm.services.wizard.types import Step, StepUpdateDTO


@dataclass(frozen=True, slots=True)
class RenderStepContext:
    process_id: ActionProcessID
    action_id: ActionID
    object: CoreObjectDescriptor


def render_step(step_id: ActionProcessStepID, context: RenderStepContext) -> None:
    process = repo.retrieve_process(process_id=context.process_id)
    step = repo.retrieve_step(process_id=context.process_id, step_id=step_id)

    step_spec_raw = repo.find_raw_step_spec(step=step, process_flow_spec=process.flow_spec)
    render_step_from_flow_spec(step=step, spec_raw=step_spec_raw, action_id=context.action_id, object_=context.object)


def render_step_from_flow_spec(
    step: Step, spec_raw: ActionProcessStep, action_id: ActionID, object_: CoreObjectDescriptor
) -> None:
    action = ActionRepoImpl.get_action(id=action_id)
    environment = RendererEnv(
        discovery_root=repo.get_bundle_root_from_prototype(prototype_id=action.owner_prototype.id)
    )

    rendered = render_template(
        template=spec_raw.template, environment=environment, action_id=action.id, object_=object_
    )
    # todo conversion is missing

    repo.update_step(step_id=step.id, data=StepUpdateDTO(step_spec=rendered))


def render_template(
    template: Template, environment: RendererEnv, action_id: ActionID, object_: CoreObjectDescriptor
) -> Any:
    renderer = get_renderer(template=template, environment=environment)
    # TODO: replace with correct context retriever; handle render error
    orm_object = core_type_to_model(object_.type).objects.get(pk=object_.id)
    context = get_env_for_jinja_config(
        action=repo.retrieve_action_orm(action_id=action_id), cluster_relative_object=orm_object
    )
    return renderer.render(context=context)
