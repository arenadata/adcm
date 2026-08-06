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

from pathlib import Path
from typing import NewType, TypedDict
import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings


class DefaultLoggingConfig(TypedDict):
    version: int
    disable_existing_loggers: bool
    filters: dict
    formatters: dict
    handlers: dict
    loggers: dict


APILoggingConfig = NewType("APILoggingConfig", dict)
SchedulerLoggingConfig = NewType("SchedulerLoggingConfig", dict)
TaskWorkerLoggingConfig = NewType("TaskWorkerLoggingConfig", dict)


_ERROR_LEVEL = logging.getLevelName(logging.ERROR)


class LoggingConfig(BaseSettings):
    log_level: str = _ERROR_LEVEL
    audit_log_level: str = logging.getLevelName(logging.INFO)
    adcm_log_level: str = _ERROR_LEVEL
    background_tasks_log_level: str = _ERROR_LEVEL
    task_runner_log_level: str = _ERROR_LEVEL
    ldap_log_level: str = _ERROR_LEVEL

    @model_validator(mode="after")
    def propagate_from_log_level_if_not_set(self):
        level_to_set = self.log_level
        fields_to_propagate_to = (
            set(self.__class__.model_fields) - self.model_fields_set - {"log_level", "audit_log_level"}
        )

        for field in fields_to_propagate_to:
            setattr(self, field, level_to_set)

        return self


def build_default_logging_config(
    config: LoggingConfig, log_dir: Path, file_handler_class: str = "logging.handlers.WatchedFileHandler"
) -> DefaultLoggingConfig:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "require_debug_false": {
                "()": "django.utils.log.RequireDebugFalse",
            },
        },
        "formatters": {
            "adcm": {
                "format": "{asctime} {levelname} {module} {message}",
                "style": "{",
            },
            "scheduler": {
                "format": "{asctime} {levelname} {name} {message}",
                "style": "{",
            },
        },
        "handlers": {
            # files
            "job_scheduler_file_handler": {
                "class": "logging.handlers.WatchedFileHandler",
                "formatter": "scheduler",
                "filename": log_dir / "scheduler.log",
            },
            "adcm_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "adcm.log",
            },
            "adcm_debug_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "adcm_debug.log",
            },
            "task_runner_err_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "task_runner.err",
            },
            "background_task_file_handler": {
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "cron_task.log",
            },
            "ldap_file_handler": {
                "class": file_handler_class,
                "formatter": "adcm",
                "filename": log_dir / "ldap.log",
            },
            # streams
            "stream_stdout_handler": {
                "class": "logging.StreamHandler",
                "formatter": "adcm",
                "stream": "ext://sys.stdout",
            },
            "stream_stderr_handler": {
                "class": "logging.StreamHandler",
                "formatter": "adcm",
                "stream": "ext://sys.stderr",
            },
            # special
            "audit_file_handler": {
                "class": file_handler_class,
                "filename": log_dir / "audit.log",
            },
        },
        "loggers": {
            "audit": {
                "handlers": ["audit_file_handler"],
                "level": config.audit_log_level,
                "propagate": True,
            },
        },
    }
