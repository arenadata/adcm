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
from typing import TypedDict, cast
import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

from application.environment import directories_from_env


class DefaultLoggingConfig(TypedDict):
    version: int
    disable_existing_loggers: bool
    filters: dict
    formatters: dict
    handlers: dict
    loggers: dict


_ERROR_LEVEL = logging.getLevelName(logging.ERROR)
_FORMATTERS = {
    "adcm": {
        "format": "{asctime} {levelname} {module} {message}",
        "style": "{",
    },
    "scheduler": {
        "format": "{asctime} {levelname} {name} {message}",
        "style": "{",
    },
    "only-message": {
        "format": "{message}",
        "style": "{",
    },
}
_HANDLERS_STREAM = {
    "stream.print": {
        "class": "logging.StreamHandler",
        "formatter": "only-message",
        "stream": "ext://sys.stdout",
    },
    "stream.stderr": {
        "class": "logging.StreamHandler",
        "formatter": "adcm",
        "stream": "ext://sys.stderr",
    },
}


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
        "formatters": _FORMATTERS,
        "handlers": {
            # files
            "file.scheduler": {
                "formatter": "scheduler",
                "class": file_handler_class,
                "filename": log_dir / "scheduler.log",
            },
            "file.adcm": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "adcm.log",
            },
            "file.adcm-debug": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "adcm_debug.log",
            },
            "file.task-runner": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "task_runner.err",
            },
            "file.background-task": {
                "formatter": "adcm",
                "class": file_handler_class,
                "filename": log_dir / "cron_task.log",
            },
            "file.ldap": {
                "class": file_handler_class,
                "formatter": "adcm",
                "filename": log_dir / "ldap.log",
            },
            # streams
            **_HANDLERS_STREAM,
            # special
            "file.audit": {
                "class": file_handler_class,
                "filename": log_dir / "audit.log",
            },
        },
        "loggers": {
            "audit": {
                "handlers": ["file.audit"],
                "level": config.audit_log_level,
                "propagate": False,
            },
        },
    }


def api_logging_config_from_env() -> dict:
    config = LoggingConfig()
    directories = directories_from_env()

    default_config = build_default_logging_config(config=config, log_dir=directories.logs)
    default_config["loggers"] |= {
        # our
        "adcm": {
            "handlers": ["file.adcm"],
            "level": config.adcm_log_level,
            "propagate": True,
        },
        "background-tasks": {
            "handlers": ["file.background-task"],
            "level": config.background_tasks_log_level,
            "propagate": True,
        },
        "task-runner": {
            "handlers": ["file.task-runner"],
            "level": config.task_runner_log_level,
            "propagate": True,
        },
        # django
        "django": {
            "handlers": ["file.adcm-debug"],
            "level": config.adcm_log_level,
            "propagate": True,
        },
        "django_auth_ldap": {
            "handlers": ["file.ldap"],
            "level": config.ldap_log_level,
            "propagate": True,
        },
    }
    return cast(dict, default_config)


def scheduler_logging_config_from_env() -> dict:
    config = LoggingConfig()
    directories = directories_from_env()

    default_config = build_default_logging_config(config=config, log_dir=directories.logs)
    default_config["loggers"]["scheduler"] = {
        "handlers": ["file.scheduler"],
        "level": config.log_level,
        "propagate": True,
    }
    return cast(dict, default_config)


def startup_logging_config_from_env() -> dict:
    config = LoggingConfig()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": _FORMATTERS,
        "handlers": _HANDLERS_STREAM,
        "loggers": {
            # use to to write messages to stdout in startup scripts, it has the simpliest format possible
            "startup.message": {"propagate": False, "level": logging.INFO, "handlers": ["stream.print"]},
            # use this to log progress of startup scripts (regular logging)
            "startup.flow": {"propagate": False, "level": config.adcm_log_level, "handlers": ["stream.stderr"]},
        },
    }


def task_worker_logging_config_from_env() -> dict:
    config = LoggingConfig()
    directories = directories_from_env()

    # ensure obligatory loggers are initialized, but don't configure extra ones: worker and so on,
    # just rely on default logger configuration
    default_config = build_default_logging_config(config=config, log_dir=directories.logs)
    return cast(dict, default_config)
