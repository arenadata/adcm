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
import logging

from adcm.mixins import ParentObject
from core.bundle_alt.process import ScriptJinjaContext, parse_scripts_jinja
from core.job.dto import LogCreateDTO, TaskPayloadDTO
from core.job.types import ActionInfo
from core.types import ActionTargetDescriptor
from django.db.transaction import atomic
from django.utils import timezone

from cm.converters import orm_object_to_core_descriptor
from cm.models import Process, ProcessStep, ProcessStepInput, ProcessStepState
from cm.services.job.run.repo import JobRepoImpl
from cm.services.wizard import repo
from cm.services.wizard.operations import revoke_next_steps
from cm.services.wizard.types import ProcessToChangeDTO


@atomic
def operation_submit_job(
    process: ProcessToChangeDTO,
    step_id: int,
    *,
    parent_object: ParentObject,  # target == owner, Cluster, Service, Component, Provider, Host / ???ActionHostGroup???
    action: ActionInfo,
) -> None:
    step = repo.retrieve_step(process_id=process.id, step_id=step_id)

    job_repo = JobRepoImpl

    owner = orm_object_to_core_descriptor(object_=parent_object)  # target == owner
    target = ActionTargetDescriptor(id=owner.id, type=owner.type)
    payload = TaskPayloadDTO()

    task = job_repo.create_task(target=target, owner=owner, action=action, payload=payload)
    logging.getLogger("adcm").error(f"{task.action=}")

    process_ = repo.retrieve_process(process_id=process.id)

    step_raw_spec = repo.find_step_spec(step=step, process_flow_spec=process_.flow_spec)

    bundle_root_path = repo.get_bundle_root_from_prototype(prototype_id=parent_object.prototype_id)
    action_orm = repo.retrieve_action_orm(action_id=action.id)  # ???
    context = ScriptJinjaContext(
        source_dir=bundle_root_path / step_raw_spec.template.file.path,
        action_allow_to_terminate=action_orm.allow_to_terminate,
    )

    jobs = list(parse_scripts_jinja(data=step.step_spec, context=context))

    job_repo.create_jobs(task_id=task.id, jobs=jobs)

    logs = []
    for job in job_repo.get_task_jobs(task_id=task.id):
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

    if logs:
        job_repo.create_logs(logs)

    task_orm = repo.retrieve_task_orm(task_id=task.id)
    logging.getLogger("adcm").error(f"{task_orm.action=}")

    data = {"step_id": step_id, "configuration": None, "job_id": task_orm.id, "created_at": timezone.now()}
    step_input_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not step_input_qs.exists():
        ProcessStepInput.objects.create(**data)
    else:
        step_input_qs.update(**data)

    revoke_next_steps(process_id=process.id, step_id=step_id)
    ProcessStep.objects.filter(id=step_id).update(state=ProcessStepState.RUNNING)
    Process.objects.filter(id=process.id).update(hash=uuid4(), last_completed_step_id=step_id)

    # todo write pid to task (executor)
    # start_task(task=task_orm)
