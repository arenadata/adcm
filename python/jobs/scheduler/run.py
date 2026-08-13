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

from dataclasses import dataclass
from datetime import timedelta
from multiprocessing import Process
from typing import Protocol
import os
import sys
import logging.config

from application.loggers import scheduler_logging_config_from_env
from core.action.scheduler import Clock
from dishka import make_container

sys.path.append("/adcm/python")

import adcm.init_django  # noqa

from application.di.containers import get_main_providers
from application.di.providers.scheduler import SchedulerProvider
from use_cases.job.scheduler import Killer, Launcher, Monitor

from jobs.scheduler.settings import SchedulerSettings

logger = logging.getLogger("scheduler.main")


class Iteration(Protocol):
    def do(self) -> None:
        ...


@dataclass(slots=True)
class SchedulerLoop:
    iteration: Iteration
    clock: Clock
    component_name: str
    logger: logging.Logger

    def run_in_loop(self) -> None:
        self.logger.info("%s started (pid: %s)", self.component_name, os.getpid())

        while True:
            self.clock.sleep_until_next_tick()

            try:
                self.iteration.do()
            except Exception:  # noqa: BLE001
                self.logger.exception("%s iteration failed", self.component_name)


def main() -> None:
    logging.config.dictConfig(scheduler_logging_config_from_env())
    logger.info("Scheduler started (pid: %d)", os.getpid())

    container = make_container(SchedulerProvider(), *get_main_providers())

    settings = container.get(SchedulerSettings)

    monitor = SchedulerLoop(
        iteration=container.get(Monitor),
        clock=Clock(period=timedelta(seconds=settings.job_monitor_poll_interval)),
        component_name="Monitor",
        logger=logging.getLogger("scheduler.monitor"),
    )
    launcher = SchedulerLoop(
        iteration=container.get(Launcher),
        clock=Clock(period=timedelta(seconds=settings.job_launch_poll_interval)),
        component_name="Launcher",
        logger=logging.getLogger("scheduler.launcher"),
    )
    killer = SchedulerLoop(
        iteration=container.get(Killer),
        clock=Clock(period=timedelta(seconds=settings.job_termination_poll_interval)),
        component_name="Killer",
        logger=logging.getLogger("scheduler.killer"),
    )

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
