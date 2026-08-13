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

from datetime import timedelta

from core.action import TaskRunnerEnvironment
from core.action.scheduler import TaskMonitorRegistry, TaskQueuer, TerminatorRegistry
from dishka import Provider, Scope, provide, provide_all
from integrations.celery.scheduler import CeleryMonitorTrustGap, CeleryTaskMonitor, CeleryTaskQueuer, CeleryTerminator
from integrations.local.scheduler import LocalTaskMonitor, LocalTaskQueuer, LocalTerminator
from jobs.scheduler import repo as scheduler_repo
from jobs.scheduler.settings import SchedulerSettings
from use_cases.job.scheduler import Killer, Launcher, Monitor


class SchedulerProvider(Provider):
    scope = Scope.APP

    various = provide_all(
        LocalTerminator, CeleryTerminator, Monitor, Launcher, Killer, LocalTaskMonitor, CeleryTaskMonitor
    )

    @provide
    def job_trust_gap(self, settings: SchedulerSettings) -> CeleryMonitorTrustGap:
        return CeleryMonitorTrustGap(timedelta(seconds=settings.job_inactivity_threshold))

    @provide
    def killer_registry(self, local: LocalTerminator, celery: CeleryTerminator) -> TerminatorRegistry:
        return {TaskRunnerEnvironment.LOCAL: local, TaskRunnerEnvironment.CELERY: celery}

    @provide
    def monitor_registry(self, local: LocalTaskMonitor, celery: CeleryTaskMonitor) -> TaskMonitorRegistry:
        return {TaskRunnerEnvironment.LOCAL: local, TaskRunnerEnvironment.CELERY: celery}

    @provide
    def queuer(self, settings: SchedulerSettings) -> TaskQueuer:
        match settings.job_execution_environment:
            case TaskRunnerEnvironment.LOCAL:
                return LocalTaskQueuer()
            case TaskRunnerEnvironment.CELERY:
                return CeleryTaskQueuer()

    @provide
    def scheduler_repo(self) -> scheduler_repo.SchedulerRepo:
        return scheduler_repo.SchedulerRepo(scheduler_repo)
