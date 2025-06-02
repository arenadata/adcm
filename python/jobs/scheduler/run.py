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
from pathlib import Path
from time import sleep
import os
import sys
import logging
import logging.config

sys.path.append("/adcm/python")
from jobs.scheduler.launcher import run_launcher_in_loop
from jobs.scheduler.monitor import Monitor

LOG_DIR = Path(__file__).absolute().parent.parent.parent.parent / "data" / "log"
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", logging.getLevelName(logging.ERROR))
LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "adcm": {
            "format": "{asctime} {levelname} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "job_scheduler_file_handler": {
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "adcm",
            "filename": LOG_DIR / "scheduler.log",
        },
    },
    "loggers": {
        "job_scheduler": {
            "handlers": ["job_scheduler_file_handler"],
            "level": DEFAULT_LOG_LEVEL,
            "propagate": True,
        },
    },
}
logging.config.dictConfig(LOGGER_CONFIG)

logger = logging.getLogger("job_scheduler")


def main() -> None:
    logger.info(f"Scheduler started (pid: {os.getpid()})")

    proc = Process(target=run_launcher_in_loop, args=())
    proc.start()

    monitor = Monitor()
    proc = Process(target=monitor, args=())
    proc.start()

    while True:
        sleep(60)


if __name__ == "__main__":
    main()
