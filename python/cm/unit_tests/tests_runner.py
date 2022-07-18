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

from django.utils import timezone
from cm.bundle import load_adcm
from cm.models import TaskLog, JobLog, Bundle, Prototype, Action


class PreparationData:
    def __init__(self, number_tasks, number_jobs):
        self.number_tasks = number_tasks
        self.number_jobs = number_jobs
        self.tasks = []
        self.jobs = []
        self.to_prepare()

    def to_prepare(self):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type='cluster')
        action = Action.objects.create(prototype=prototype, name='do')
        load_adcm()
        for task_id in range(1, self.number_tasks + 1):
            task_log_data = {
                'action': action,
                'object_id': task_id,
                'pid': task_id,
                'selector': {'cluster': task_id},
                'status': 'success',
                'config': '',
                'verbose': False,
                'hostcomponentmap': '',
                'start_date': timezone.now(),
                'finish_date': timezone.now(),
            }
            self.tasks.append(TaskLog.objects.create(**task_log_data))
            for jn in range(1, self.number_jobs + 1):
                job_log_data = {
                    'task_id': task_id,
                    'action': action,
                    'pid': jn + 1,
                    'selector': {'cluster': task_id},
                    'status': 'success',
                    'start_date': timezone.now(),
                    'finish_date': timezone.now(),
                }
                self.jobs.append(JobLog.objects.create(**job_log_data))

    def get_task(self, _id):
        return self.tasks[_id - 1]

    def get_job(self, _id):
        return self.jobs[_id - 1]
