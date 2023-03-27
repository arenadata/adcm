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

"""
API methods could be called from web and from ansible,
so some things should be done in different ways. Also it's painful to fetch or calc some common
things in every API method to pass it down in call stack, So it's better off to get and keep them
here during WSGI call or Ansible run

Implemented as singleton module, just `import ctx from cm.api_context` and use `ctx.*` when needed
"""

import os
from pathlib import Path

from cm import models
from cm.logger import logger
from cm.status_api import Event


class _Context:
    """Common context for API methods calls"""

    def __init__(self):
        self.event = Event()
        self.task: models.TaskLog | None = None
        self.job: models.JobLog | None = None
        self.lock: models.ConcernItem | None = None
        self.get_job_data()

    def get_job_data(self):
        env = os.environ
        ansible_config = env.get("ANSIBLE_CONFIG")
        if not ansible_config:
            return

        job_id = Path(ansible_config).parent.name
        try:
            self.job = models.JobLog.objects.select_related("task", "task__lock").get(id=int(job_id))
        except (ValueError, models.ObjectDoesNotExist):
            return

        self.task = getattr(self.job, "task", None)
        self.lock = getattr(self.task, "lock", None)
        msg = f"API context was initialized with {self.job}, {self.task}, {self.lock}"
        logger.debug(msg)


# initialized on first import
CTX = None
if not CTX:
    CTX = _Context()
