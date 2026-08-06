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

# NOTE:
#   DI in here and in worker are somewhat violation of package hierarchy,
#   but for now it's problematic to clean it up, thou probably most types and stuff must go to core,
#   leaving here only configuration/launch, when `application` can have DI.
#   On the other hand, restructuring of scheduler components (interfaces to `core`, implementations separately)
#   may be enough for this provider not to feel strange,
#   since some type it's working with (e.g. task runner environment enum) are related mostly to this entrypoint,
#   not to some `core` functionality/protocol.


from datetime import timedelta

from dishka import Provider, Scope, provide, provide_all

from jobs.scheduler import repo as scheduler_repo
from jobs.scheduler.clock import Clock
from jobs.scheduler.killer import CeleryTerminator, Killer, KillerClock, LocalTerminator, TerminatorRegistry
from jobs.scheduler.launcher import CeleryTaskQueuer, Launcher, LauncherClock, LocalTaskQueuer, TaskQueuer
from jobs.scheduler.monitor import (
    CeleryMonitorTrustGap,
    CeleryTaskMonitor,
    LocalTaskMonitor,
    Monitor,
    MonitorClock,
    TaskMonitorRegistry,
)
from jobs.scheduler.settings import SchedulerSettings
from jobs.scheduler.types import TaskRunnerEnvironment


class SchedulerProvider(Provider):
    scope = Scope.APP

    various = provide_all(
        LocalTerminator, CeleryTerminator, Monitor, Launcher, Killer, LocalTaskMonitor, CeleryTaskMonitor
    )

    @provide
    def settings(self) -> SchedulerSettings:
        # ignoring, because base settings work like that
        return SchedulerSettings()  # pyright: ignore[reportCallIssue]

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

    @provide
    def monitor_clock(self, settings: SchedulerSettings) -> MonitorClock:
        return MonitorClock(Clock(period=timedelta(seconds=settings.job_monitor_poll_interval)))

    @provide
    def launcher_clock(self, settings: SchedulerSettings) -> LauncherClock:
        return LauncherClock(Clock(period=timedelta(seconds=settings.job_launch_poll_interval)))

    @provide
    def killer_clock(self, settings: SchedulerSettings) -> KillerClock:
        return KillerClock(Clock(period=timedelta(seconds=settings.job_termination_poll_interval)))
