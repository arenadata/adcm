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

import logging

from celery.worker.control import control_command
from core.action.job import ExecutorTerminator, JobRepoI


@control_command(
    args=[("task_id", str), ("adcm_job_id", str)],
)
def stop_executor(state, task_id: str, adcm_job_id: str):
    from celery.worker.control import logger, worker_state

    job_id = int(adcm_job_id)

    logger.info('Command "stop_executor" received for celery_task_id = %s and adcm_job_id = %d', task_id, job_id)

    on_this_worker = task_id in worker_state.requests
    if not on_this_worker:
        logger.debug('Command "stop_executor" skipped due to celery task id not registered on this worker')
        return

    repo: JobRepoI = state.app.di_container.get(JobRepoI)
    job = repo.get_job(id=job_id)

    is_same_celery_id = task_id == job.execution_env.worker_id
    if not is_same_celery_id:
        logging.warning(
            'Command "stop_executor" skipped due to celery task ids mismatch (given != defined in job): %s != %s',
            task_id,
            job.execution_env.worker_id,
        )
        return

    pid = job.execution_env.pid

    if pid <= 0:
        logging.debug('Command "stop_executor" skipped due to local pid not specified (pid=%d)', pid)
        return

    terminator: ExecutorTerminator = state.app.di_container.get(ExecutorTerminator)
    terminator.terminate(pid)

    logging.debug('Command "stop_executor" finished')
