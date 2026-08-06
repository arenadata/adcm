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
import logging.config

from application.loggers import SchedulerLoggingConfig
from dishka import make_container

sys.path.append("/adcm/python")

import adcm.init_django  # noqa

from application.di.containers import get_main_providers
from jobs.worker.celery.di import CeleryProvider
from jobs.scheduler.di import SchedulerProvider

from jobs.scheduler.monitor import Monitor
from jobs.scheduler.killer import Killer
from jobs.scheduler.launcher import Launcher

logger = logging.getLogger("scheduler.main")


def main() -> None:
    container = make_container(CeleryProvider(), SchedulerProvider(), *get_main_providers())

    logging.config.dictConfig(container.get(SchedulerLoggingConfig))
    logger.info("Scheduler started (pid: %d)", os.getpid())

    monitor = container.get(Monitor)
    launcher = container.get(Launcher)
    killer = container.get(Killer)

    processes = (
        Process(target=launcher.run_in_loop),
        Process(target=monitor.run_in_loop),
        Process(target=killer.run_in_loop),
    )

    # NOTE:
    #     psycopg connections are not fork-safe, so connections must be closed before starting subprocesses.
    #     Some time ago this function opened Django's DB connection in this process.
    #     If we fork now, every child inherits and shares that same socket, corrupting its transaction state.
    #     Close it so each child opens its own with `connections.close_all()`.
    #     For now it is removed, return if problems occur again

    for proc in processes:
        proc.start()

    for proc in processes:
        proc.join()


if __name__ == "__main__":
    main()
