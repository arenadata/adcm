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


from application.di.containers import get_main_providers
from core.legacy.job.runners import JobFilterPredicate, TaskRunner, always_true
from core.types import TaskID
import dishka

from jobs.worker.celery.worker import app


@app.task(track_started=True)
def run_task(*, task_id: TaskID) -> None:
    # todo most likely container must be built once on celery start
    container = dishka.make_container(*get_main_providers())
    container_context = {JobFilterPredicate: always_true}

    container = dishka.make_container(*get_main_providers(), context=container_context)
    with container():
        runner = container.get(TaskRunner)
        runner.run(task_id=task_id)
