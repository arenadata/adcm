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

from logging import getLogger
from pathlib import Path
import os
import logging.config

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

logger = getLogger("job_scheduler")
