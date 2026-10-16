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

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from cm.models import JobStatus, TaskLog
from core.types import TaskID
from django.utils import timezone


def calculate_time_with_delta(
    delta_value: int,
    unit: Literal["seconds", "minutes", "hours", "days"] = "minutes",
    isoformat: bool = False,
    base_time: datetime | None = None,
) -> datetime | str:
    current_time = base_time or timezone.now()
    delta = timedelta(**{unit: delta_value})
    result = current_time - delta

    if isoformat:
        return result.isoformat()
    return result


def extract_from_nested_structure(data: list, value_path: str) -> list:
    """
    Extract values from nested structure.

    Example:

    >>> response = {
    ...     "results": [
    ...         {
    ...             "id": 1,
    ...             "prototype": {"name": "AAA", "status": None},
    ...             "concerns": [{"id": 3}, {"id": 4}],
    ...             "items": [
    ...                 {"stuff": [{"id": 3}, {"id": 432}]},
    ...                 {"stuff": [{"id": 4}]},
    ...             ],
    ...         }
    ...     ]
    ... }
    >>> results = response["results"]
    >>> extract_from_nested_structure(results, "id")
    [1]
    >>> extract_from_nested_structure(results, "prototype.name")
    ['AAA']
    >>> extract_from_nested_structure(results, "prototype.status")
    [None]
    >>> extract_from_nested_structure(results, "concerns.id")
    [3, 4]
    >>> extract_from_nested_structure(results, "items.stuff.id")
    [3, 432, 4]
    """

    keys = value_path.split(".")

    def _extract(current, path) -> list:
        if not path:
            return [current]

        if isinstance(current, list):
            result = []
            for item in current:
                result.extend(_extract(item, path))
            return result

        if not isinstance(current, dict):
            return []

        key = path[0]
        if key not in current:
            return []

        next_value = current[key]
        if next_value is None and path[1:]:
            return [next_value]

        return _extract(next_value, path[1:])

    result = []
    for item in data:
        result.extend(_extract(item, keys))

    return result


def assert_dict_contains_subset(subset, superset):
    """
    Check if subset contains superset, suitable only for flat dictionaries.
    Returns True if all the keys of the subset are contained in the superset.
    """

    missing_items = [item for item in subset.items() if item not in superset.items()]
    assert not any(missing_items), f"Missing items in superset: {', '.join([key for key, _ in missing_items])}"  # noqa: S101


@contextmanager
def assert_no_task_launched() -> Generator[None, None, None]:
    """
    Check that no new task appeared while the block was executed.

    Relies on task ids being monotonic, which holds for parallel runs too:
    each django test is wrapped in its own transaction.
    """

    latest_before = _latest_task_id()

    yield

    latest_after = _latest_task_id()

    assert latest_after == latest_before, f"Expected no task launched, but got #{latest_after}"  # noqa: S101


def _latest_task_id() -> int | None:
    return TaskLog.objects.order_by("-id").values_list("id", flat=True).first()


def assert_task_revoked(task_id: int) -> None:
    """
    Check that task was revoked, which is how scheduler reports validation failure:
    it doesn't raise, it sets task status instead.
    """

    status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)

    assert status == JobStatus.REVOKED, f"Expected task #{task_id} to be revoked, but it's {status}"  # noqa: S101


@dataclass(slots=True)
class LaunchedTask:
    _task_id: TaskID | None = None

    def task_id(self) -> TaskID:
        if self._task_id is None:
            message = "Task isn't registered yet, id is only available after `expect_task_launched` block is left"
            raise RuntimeError(message)

        return self._task_id

    def register(self, task_id: TaskID) -> None:
        self._task_id = task_id


@contextmanager
def expect_task_launched() -> Generator[LaunchedTask, None, None]:
    """
    Check that exactly one task was created while the block was executed
    and provide access to its id.

    Relies on task ids being monotonic, which holds for parallel runs too:
    each django test is wrapped in its own transaction.
    """

    known_task_id = _latest_task_id() or 0
    launched = LaunchedTask()

    yield launched

    new_task_ids = tuple(TaskLog.objects.filter(id__gt=known_task_id).order_by("id").values_list("id", flat=True))

    if len(new_task_ids) > 1:
        message = f"Expected one task to be launched, but got {len(new_task_ids)}: {new_task_ids}. "
        message += "Launch tasks one by one, `expect_task_launched` can't tell which one is the required one"
        raise RuntimeError(message)

    assert new_task_ids, "Expected task to be launched, but got none"  # noqa: S101

    launched.register(new_task_ids[0])
