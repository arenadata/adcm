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

from cm.models import Process, ProcessStep, PrototypeConfig
from cm.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.services.job.inventory._config import ProcessStepPair, update_configuration_for_inventory_inplace
from cm.services.job.inventory._types import CurrentStep, ProcessContext


def get_action_process_context(process: Process) -> ProcessContext:
    steps_qs = process.steps.all().select_related("processstepinput")

    steps_by_name: dict[str, ProcessStep] = {step.name: step for step in steps_qs}

    current: CurrentStep | None = None
    stages = {}

    for stage in process.flow_spec:
        stages[stage["name"]] = {}
        for step in stage["steps"]:
            step_obj = steps_by_name[step["name"]]

            if process.current_step and step_obj.id == process.current_step.id:
                current = {"step": step["name"], "stage": stage["name"]}

            if _is_config_step(step) and (step_input := getattr(step_obj, "processstepinput", None)):
                config_input = step_input.configuration

                proto_flat_spec = {
                    f"{config['name']}/{config['subname']}": PrototypeConfig(**config) for config in step_obj.step_spec
                }
                flat_spec = convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=proto_flat_spec)

                configuration = {"config": config_input["config"], "attr": config_input["attr"]}
                update_configuration_for_inventory_inplace(
                    configuration=configuration["config"],
                    attributes=configuration["attr"],
                    specification=flat_spec,
                    config_owner=ProcessStepPair(process_id=process.id, step_id=step_obj.id),
                )

                stages[stage["name"]][step["name"]] = {"config": configuration}

    return ProcessContext(stages=stages, current=current)


def _is_config_step(step: dict) -> bool:
    # left this check as there's no "type" field for now in step spec/obj
    return "config_template" in step
