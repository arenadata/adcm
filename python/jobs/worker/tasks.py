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

from cm.models import TaskLog
from cm.services.job.run import run_task_in_local_subprocess
from django.db.transaction import atomic

from jobs.worker.app import app


@app.task()
def run_job(job_id: int) -> None:
    # name and arguments are new, but in function naming is old
    # `job_id` is `tasklog_id`
    with atomic():
        task = TaskLog.objects.get(id=job_id)
        run_task_in_local_subprocess(task=task, command="start")
