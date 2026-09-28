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

from datetime import UTC, datetime, timedelta
from typing import Final
from unittest import TestCase

from core.action.types import RuntimeDates

MOMENT: Final = datetime(2026, 8, 12, 10, 31, 2, tzinfo=UTC)


class TestRuntimeDates(TestCase):
    def test_duration_unknown_until_both_dates_are_known(self) -> None:
        for dates in (RuntimeDates(), RuntimeDates(start=MOMENT), RuntimeDates(finish=MOMENT)):
            with self.subTest(dates=dates):
                self.assertIsNone(dates.duration)

    def test_duration_is_seconds_between_start_and_finish(self) -> None:
        dates = RuntimeDates(start=MOMENT, finish=MOMENT + timedelta(seconds=12, milliseconds=500))

        self.assertEqual(dates.duration, 12.5)

    def test_duration_of_instant_job_is_zero(self) -> None:
        self.assertEqual(RuntimeDates(start=MOMENT, finish=MOMENT).duration, 0)
