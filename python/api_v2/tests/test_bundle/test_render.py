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
from functools import partial
from typing import Callable, Generic, Iterable, TypeVar

from cm.errors import HTTP_409_CONFLICT
from cm.models import Action, Process, ProcessStep
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from tests.suites import ADCMDjangoAPISuite
import core

from api_v2.tests.base import APIV2Mixin
from api_v2.utils.di import prepare_container

T = TypeVar("T")


@dataclass(slots=True)
class RenderErrorCase(Generic[T]):
    name: str
    perform: Callable[[], T]
    check: Callable[[T], None]


class TestRenderErrors(APIV2Mixin, ADCMDjangoAPISuite):
    def setUp(self) -> None:
        super().setUp()

        prepare_container.cache_clear()

        bundle = self.create_bundle(self.test_bundles_dir / "render_errors")
        self.cluster = self.create_cluster(bundle=bundle, name="aaa")

    def get_action(self, action: Action) -> Response:
        return self.client.v2[self.cluster, "actions", action.pk].get()

    def start_action(self, action: Action) -> Response:
        return self.client.v2[self.cluster, "actions", action.pk, "run"].post()

    def start_process(self, action: Action) -> Response:
        return self.client.v2[self.cluster, "actions", action.pk, "processes"].post()

    def start_process_successfully(self, action: Action) -> Process:
        response = self.client.v2[self.cluster, "actions", action.pk, "processes"].post()
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())
        return Process.objects.get(id=response.json()["id"])

    def check_response_is_failed(self, response: Response) -> None:
        expected_code: str = "BUNDLE_DEFINITION_ERROR"
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], expected_code)

    def check_started_process_and_first_step(self, process: Process) -> None:
        self.assertEqual(process.state, core.action.wizard.ProcessState.CREATED)
        first_step = ProcessStep.objects.get(process=process)
        self.assertEqual(first_step.state, core.action.wizard.StepState.BROKEN)

    def build_cases(self, actions: Iterable[Action]) -> list[RenderErrorCase]:
        cases = []

        for action in actions:
            name = action.name
            _, *parts = name.split("_")

            match parts:
                case ["syntax" | "render", "py" | "yaml", "config", *_]:
                    case = RenderErrorCase(
                        name=name, perform=partial(self.get_action, action=action), check=self.check_response_is_failed
                    )

                case ["syntax" | "render", "py" | "yaml", "scripts", *_]:
                    case = RenderErrorCase(
                        name=name,
                        perform=partial(self.start_action, action=action),
                        # if not 409, further tests may fail
                        check=self.check_response_is_failed,
                    )

                case ["syntax" | "render", "py" | "yaml", "wizard", *_]:
                    case = RenderErrorCase(
                        name=name,
                        perform=partial(self.start_process, action=action),
                        check=self.check_response_is_failed,
                    )

                case ["syntax" | "render", "py" | "yaml", "step" | "wizard", *_]:
                    case = RenderErrorCase(
                        name=name,
                        perform=partial(self.start_process_successfully, action=action),
                        check=self.check_started_process_and_first_step,
                    )

                case ["missing", "file", "step", *_]:
                    case = RenderErrorCase(
                        name=name,
                        perform=partial(self.start_process_successfully, action=action),
                        check=self.check_started_process_and_first_step,
                    )

                case _:
                    raise ValueError(f"Unknown case: {parts=}")

            cases.append(case)

        if not cases:
            raise RuntimeError(f"cases are empty for {actions=}")

        return cases

    def test_cases(self):
        prefix = "error_"
        actions = Action.objects.filter(name__startswith=prefix, prototype_id=self.cluster.prototype_id)
        cases = self.build_cases(actions)

        for case in cases:
            with self.subTest(case.name):
                result = case.perform()
                case.check(result)
