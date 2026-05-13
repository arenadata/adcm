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

from contextlib import contextmanager
from typing import Generator

from dishka import Container, Scope, make_container


# very dumb implementation for container dependencies builder,
# should be used only for old cases that already are neck deep in dependencies
class WithDishkaContainer:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._container: Container | None = None

    @contextmanager
    def container(self) -> Generator[Container, None, None]:
        if self._container:
            container = self._container
        else:
            container = self._make_container()
            self._container = container

        with container(scope=Scope.REQUEST) as c:
            yield c

    def _make_container(self) -> Container:
        # should be moved in commmon place
        from application.di.containers import get_main_providers
        from tests.dependencies import EnvironmentOverride, TaskStarterOverride

        providers = get_main_providers()

        return make_container(*providers, TaskStarterOverride(), EnvironmentOverride())
