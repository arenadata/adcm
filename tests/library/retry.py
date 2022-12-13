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

"""Utilities for retrying operations that require some context"""

from dataclasses import dataclass, field
from time import sleep
from typing import Any, Callable, Collection

import allure


@dataclass()
class Step:
    """
    Wrapper to a test step or state restoration step
    """

    func: Callable
    args: Collection[Any] = ()
    kwargs: dict[Any, Any] = field(default_factory=dict)

    def exec(self) -> Any:
        """Execute wrapped function"""
        return self.func(*self.args, **self.kwargs)


class RetryFromCheckpoint:
    """
    In some cases simple "assertion retry" isn't good enough (especially for UI tests)
    AND we can "retry" some operation after restoring "initial" state.
    That's what this class is made for.

    It's a work in progress, so there changes may and will be done.
    """

    def __init__(self, execution_steps: Collection[Step], restoration_steps: Collection[Step]):
        self._execution_steps = tuple(execution_steps)
        self._restoration_steps = tuple(restoration_steps)

    def __call__(self, restore_from: Exception | tuple[Exception], max_retries: int = 3, *, counter: int = 0) -> None:
        try:
            for step in self._execution_steps:
                step.exec()

        except restore_from as e:
            if counter >= max_retries:
                raise

            with allure.step(f"Caught exception {e}, restoring state"):
                for step in self._restoration_steps:
                    step.exec()
                    self(restore_from, max_retries, counter=counter + 1)


def should_become_truth(check: Callable[..., bool], retries: int = 3, period: int | float = 0.5, **kwargs) -> None:
    for _ in range(retries):
        if check(**kwargs):
            return
        sleep(period)

    raise AssertionError(f"Check failed with {retries} attempts")
