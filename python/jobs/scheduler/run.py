#!/usr/bin/env python3

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

from multiprocessing import Process
import os
import sys

sys.path.append("/adcm/python")
from jobs.scheduler.launcher import run_launcher_in_loop
from jobs.scheduler.logger import logger
from jobs.scheduler.monitor import run_monitor_in_loop
from jobs.scheduler.recover import actualize_locks


def main() -> None:
    logger.info(f"Scheduler started (pid: {os.getpid()})")

    actualize_locks()

    launcher_proc = Process(target=run_launcher_in_loop, args=())
    launcher_proc.start()

    monitor_proc = Process(target=run_monitor_in_loop, args=())
    monitor_proc.start()

    for proc in (launcher_proc, monitor_proc):
        proc.join()


if __name__ == "__main__":
    main()
