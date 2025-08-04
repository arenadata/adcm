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

from uuid import uuid4

from adcm.mixins import ParentObject
from core.job.types import ActionInfo
from core.types import ActionProcessStepID
from django.db.transaction import atomic
from django.utils import timezone

from cm.models import Process, ProcessStep, ProcessStepInput, ProcessStepState
from cm.services.config import ConfigAttrPair
from cm.services.wizard.operations import revoke_next_steps
from cm.services.wizard.types import ProcessToChangeDTO


@atomic
def operation_submit_config(
    process: ProcessToChangeDTO,
    step_id: ActionProcessStepID,
    configuration: ConfigAttrPair,
    *,
    parent_object: ParentObject,
    action: ActionInfo,
) -> None:
    _ = parent_object, action

    data = {"step_id": step_id, "configuration": configuration._asdict(), "job": None, "created_at": timezone.now()}
    step_input_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not step_input_qs.exists():
        ProcessStepInput.objects.create(**data)
    else:
        step_input_qs.update(**data)

    revoke_next_steps(process_id=process.id, step_id=step_id)
    ProcessStep.objects.filter(id=step_id).update(state=ProcessStepState.SUCCESS)
    Process.objects.filter(id=process.id).update(hash=uuid4(), last_completed_step_id=step_id)
