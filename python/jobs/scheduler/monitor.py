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

import os
import time

from jobs.scheduler._logger import logger
from jobs.scheduler._types import Monitor, TaskRunnerEnvironment


class LocalMonitor(Monitor):
    def __call__(self, *args, **kwargs):
        _ = args, kwargs
        logger.info(f"LocalMonitor started (pid: {os.getpid()})")
        self.run()

    def run(self):
        while True:
            logger.info("LocalMonitor.run")
            time.sleep(500)


class CeleryMonitor(Monitor):
    def __call__(self, *args, **kwargs):
        _ = args, kwargs
        logger.info(f"CeleryMonitor started (pid: {os.getpid()})")
        self.run()

    def run(self):
        while True:
            logger.info("CeleryMonitor.run")
            time.sleep(500)


MONITOR_REGISTRY = {
    TaskRunnerEnvironment.LOCAL: LocalMonitor,
    TaskRunnerEnvironment.CELERY: CeleryMonitor,
}
