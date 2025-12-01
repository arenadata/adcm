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

from core.types import ActionProcessID, ActionProcessStepID, Descriptor, ObjectID, TaskID


def build_config_prefix(owner: Descriptor) -> str:
    return f"{owner.type.value.lower()}.{owner.id}"


def build_config_host_group_prefix(owner: Descriptor, group_id: ObjectID) -> str:
    prefix = build_config_prefix(owner)
    return f"{prefix}.group.{group_id}"


def build_action_process_step_prefix(process_id: ActionProcessID, step_id: ActionProcessStepID) -> str:
    return f"process.{process_id}.step.{step_id}"


def construct_parameter_file_name(parameter_file_identifier: str, owner: Descriptor) -> str:
    owner_prefix = build_config_prefix(owner)
    return f"{owner_prefix}.{parameter_file_identifier}"


def construct_parameter_file_name_for_host_group(
    parameter_file_identifier: str, owner: Descriptor, group_id: ObjectID
) -> str:
    prefix = build_config_host_group_prefix(owner=owner, group_id=group_id)
    return f"{prefix}.{parameter_file_identifier}"


def construct_parameter_file_name_for_task(parameter_file_identifier: str, task_id: TaskID) -> str:
    return f"task.{task_id}.{parameter_file_identifier}"


def construct_parameter_file_name_for_action_process_step(
    parameter_file_identifier: str, process_id: ActionProcessID, step_id: ActionProcessStepID
) -> str:
    prefix = build_action_process_step_prefix(process_id=process_id, step_id=step_id)
    return f"{prefix}.{parameter_file_identifier}"
