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

from dishka import make_container

sys.path.append("/adcm/python")
import adcm.init_django  # noqa
from application.di.containers import get_main_providers
from cm.transition.action import RetrieveStartImpossibleReason
from django.db import connections

from jobs.scheduler.launcher import run_launcher_in_loop
from jobs.scheduler.logger import logger
from jobs.scheduler.monitor import run_monitor_in_loop
from jobs.scheduler.recover import actualize_locks


def main() -> None:
    logger.info(f"Scheduler started (pid: {os.getpid()})")

    actualize_locks()

    container = make_container(*get_main_providers())
    retrieve_sir = container.get(RetrieveStartImpossibleReason)

    processes = [
        Process(target=run_launcher_in_loop, args=(retrieve_sir,)),
        Process(target=run_monitor_in_loop, args=()),
    ]

    # psycopg connections are not fork-safe. `actualize_locks()` and container
    # setup above opened Django's DB connection in this parent process; if we
    # fork now, every child inherits and shares that same socket, corrupting its
    # transaction state. Close it so each child opens its own.
    connections.close_all()

    for proc in processes:
        proc.start()

    for proc in processes:
        proc.join()


if __name__ == "__main__":
    main()
