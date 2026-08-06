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

from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobs.scheduler.types import TaskRunnerEnvironment


class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="scheduler_")

    # poll_interval in seconds
    job_launch_poll_interval: Annotated[int, Field(default=1, ge=1)]
    job_monitor_poll_interval: Annotated[int, Field(default=60, ge=1)]
    job_termination_poll_interval: Annotated[int, Field(default=5, ge=1)]

    # threshold to consider tasks dead when last job was finished more than this value ago (in seconds)
    job_inactivity_threshold: Annotated[int, Field(default=30, ge=1)]

    job_execution_environment: TaskRunnerEnvironment = TaskRunnerEnvironment.LOCAL
