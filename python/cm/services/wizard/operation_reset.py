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

from core.types import ActionProcessStepID
from django.db.transaction import atomic

from cm.models import Process, ProcessStep, ProcessStepState
from cm.services.wizard.operations import revoke_starting_with_step
from cm.services.wizard.types import ProcessToChangeDTO


@atomic
def operation_reset(process: ProcessToChangeDTO, step_id: ActionProcessStepID) -> None:
    revoke_starting_with_step(process.id, step_id)
    # Here we rely on process steps bulk_create behavior:
    # ids of created rows are preserves the definition order in process.flow_spec
    # so min(revoked_steps) is previous step
    last_completed_step_id = ProcessStep.objects.filter(state=ProcessStepState.SUCCESS).order_by("-id").first()
    Process.objects.filter(id=process.id).update(hash=uuid4(), last_completed_step_id=last_completed_step_id)
