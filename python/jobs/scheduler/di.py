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


from dishka import Provider, Scope, provide

from jobs.scheduler._types import TaskRunnerEnvironment
from jobs.scheduler.killer import CeleryKiller, KillerRegistry, LocalKiller


class SchedulerProvider(Provider):
    scope = Scope.APP

    local_killer = provide(LocalKiller)
    celery_killer = provide(CeleryKiller)

    @provide
    def killer_registry(self, local: LocalKiller, celery: CeleryKiller) -> KillerRegistry:
        return {TaskRunnerEnvironment.LOCAL: local, TaskRunnerEnvironment.CELERY: celery}
