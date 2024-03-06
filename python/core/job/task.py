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


from core.job.dto import LogCreateDTO, TaskPayloadDTO
from core.job.repo import ActionRepoInterface, JobRepoInterface
from core.job.types import JobSpec
from core.types import ActionID, CoreObjectDescriptor


def compose_task(
    target: CoreObjectDescriptor,
    owner: CoreObjectDescriptor,
    action: ActionID,
    payload: TaskPayloadDTO,
    job_repo: JobRepoInterface,
    action_repo: ActionRepoInterface,
):
    """
    Prepare task based on action, target object and task payload.

    Target object is an object on which action is going to be launched, not the on it's described on.

    `Task` is launched action, "task for ADCM to perform action" in other words.
    `Job` is an actual piece of work required by task to be performed.

    ! WARNING !
    Currently, stdout/stderr logs are created alongside the jobs
    for policies to be re-applied correctly after this method is called.
    It must be changed.
    """

    job_specifications = get_specifications_for_jobs(action=action, repo=action_repo)
    if not job_specifications:
        # todo fix error type
        message = f"Can't compose task for action #{action}, because no associated jobs found"
        raise RuntimeError(message)

    action_info = action_repo.get_action(id=action)
    task = job_repo.create_task(target=target, owner=owner, action=action_info, payload=payload)

    job_repo.create_jobs(task_id=task.id, jobs=job_specifications)

    # todo fix warning from docstring
    logs = []
    for job in job_repo.get_task_jobs(task_id=task.id):
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

    if logs:
        job_repo.create_logs(logs)

    return task


def get_specifications_for_jobs(action: ActionID, repo: ActionRepoInterface) -> tuple[JobSpec, ...]:
    # jinja_scripts will be used here
    return tuple(repo.get_job_specs(id=action))
