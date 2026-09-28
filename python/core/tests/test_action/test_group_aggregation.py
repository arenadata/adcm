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

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from core.action.job.operations import aggregate_group_dates, aggregate_group_status
from core.action.types import ExecutionStatus, RuntimeDates

ABORTED = ExecutionStatus.ABORTED
BROKEN = ExecutionStatus.BROKEN
CREATED = ExecutionStatus.CREATED
FAILED = ExecutionStatus.FAILED
QUEUED = ExecutionStatus.QUEUED
REVOKED = ExecutionStatus.REVOKED
REVOKING = ExecutionStatus.REVOKING
RUNNING = ExecutionStatus.RUNNING
SCHEDULED = ExecutionStatus.SCHEDULED
SUCCESS = ExecutionStatus.SUCCESS
TERMINATING = ExecutionStatus.TERMINATING

BASE = datetime(2026, 8, 12, 10, 30, tzinfo=timezone.utc)
NO_DATES = RuntimeDates()


def at(seconds: int) -> datetime:
    return BASE + timedelta(seconds=seconds)


def ran(start: int, finish: int | None = None) -> RuntimeDates:
    return RuntimeDates(start=at(start), finish=None if finish is None else at(finish))


# children's statuses | derived group status
STATUS_CASES: tuple[tuple[list[ExecutionStatus], ExecutionStatus], ...] = (
    # anything in progress makes the group running, whatever else is there
    ([SUCCESS, RUNNING], RUNNING),
    ([SUCCESS, SCHEDULED], RUNNING),
    ([SUCCESS, QUEUED], RUNNING),
    ([SUCCESS, REVOKING], RUNNING),
    ([SUCCESS, TERMINATING], RUNNING),
    ([FAILED, RUNNING], RUNNING),
    ([BROKEN, RUNNING], RUNNING),
    # failure beats everything settled and not started
    ([SUCCESS, BROKEN], FAILED),
    ([BROKEN], FAILED),
    ([FAILED, ABORTED], FAILED),
    ([FAILED, REVOKED], FAILED),
    ([BROKEN, ABORTED], FAILED),
    ([BROKEN, REVOKED], FAILED),
    ([FAILED, CREATED], FAILED),
    # nothing started yet
    ([CREATED, CREATED], CREATED),
    # some started, some not: running, whatever state the task is in
    ([SUCCESS, CREATED], RUNNING),
    ([ABORTED, CREATED], RUNNING),
    # settled mixes
    ([SUCCESS, SUCCESS, SUCCESS], SUCCESS),
    ([REVOKED, REVOKED], REVOKED),
    ([SUCCESS, ABORTED], ABORTED),
    ([SUCCESS, REVOKED], ABORTED),
    ([ABORTED, REVOKED], ABORTED),
)

# children's dates | derived group dates
DATES_CASES: tuple[tuple[list[RuntimeDates], RuntimeDates], ...] = (
    # start is the earliest known, end the latest one once every child has finished
    ([ran(10, 20), ran(5, 15), ran(30, 40)], ran(5, 40)),
    # a child without an end (not started, still running or never finished) leaves the group's end unknown
    ([ran(10, 20), NO_DATES, ran(5, 15), ran(30, 40)], RuntimeDates(start=at(5))),
    ([ran(0, 12), ran(12, 30), NO_DATES], RuntimeDates(start=at(0))),
    ([ran(0, 7), NO_DATES], RuntimeDates(start=at(0))),
    ([ran(0, 10), ran(10)], RuntimeDates(start=at(0))),
    ([ran(0, 10), ran(20)], RuntimeDates(start=at(0))),
    # no child ever ran
    ([NO_DATES, NO_DATES], NO_DATES),
)


class TestAggregateGroupStatus(TestCase):
    def test_status_cases(self) -> None:
        for children, expected in STATUS_CASES:
            with self.subTest(children=children):
                self.assertEqual(aggregate_group_status(children), expected)


class TestAggregateGroupDates(TestCase):
    def test_dates_cases(self) -> None:
        for children, expected in DATES_CASES:
            with self.subTest(children=children):
                dates = aggregate_group_dates(children=children)

                self.assertEqual(dates, expected)
                self.assertEqual(dates.duration, expected.duration)
