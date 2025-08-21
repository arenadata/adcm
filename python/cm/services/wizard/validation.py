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

from typing import TypeAlias
from uuid import UUID

from core.types import ActionProcessID

from cm.services.wizard import repo
from cm.services.wizard.errors import NotCurrentStepSubmissionError, SyncKeyMismatchError
from cm.services.wizard.operations import retrieve_current_step_id
from cm.services.wizard.schema_validation import (
    CompleteStepPayload,
    ProcessOperationType,
    ResetStepPayload,
    SubmitStepPayload,
)
from cm.services.wizard.types import ActionProcess

OperationPayload: TypeAlias = SubmitStepPayload | CompleteStepPayload | ResetStepPayload


def validate_operation(process_id: ActionProcessID, payload: OperationPayload) -> None:
    process: ActionProcess = repo.retrieve_process(process_id=process_id)

    _check_sync_key(sync_key=payload.params.process_sync_key, process=process)

    match payload.method:
        case ProcessOperationType.SUBMIT:
            _validate_submit(process=process, payload=payload)
        case ProcessOperationType.COMPLETE:
            pass  # TODO
        case ProcessOperationType.RESET:
            pass  # TODO


def _validate_submit(process: ActionProcess, payload: SubmitStepPayload) -> None:
    step = repo.retrieve_step(process_id=process.id, step_id=payload.params.step_id)
    current_step_id = retrieve_current_step_id(process_id=process.id)

    if step.id != current_step_id:
        raise NotCurrentStepSubmissionError()


def _check_sync_key(sync_key: UUID, process: ActionProcess) -> None:
    if process.sync_key != sync_key:
        raise SyncKeyMismatchError()
