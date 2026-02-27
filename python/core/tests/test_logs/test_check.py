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

from unittest import TestCase

from core.logs._operations import aggregate_check_logs_results_for_group
from core.logs._types import CheckLogResult, Severity


class TestCheckLog(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

    def test_aggregate_check_logs_result_for_group_warning(self):
        check_log_results = [
            CheckLogResult(result=True, severity=Severity.ERROR),
            CheckLogResult(result=False, severity=Severity.WARNING),
        ]

        result = aggregate_check_logs_results_for_group(check_log_results=check_log_results)

        self.assertEqual(result, CheckLogResult(result=False, severity=Severity.WARNING))

    def test_aggregate_check_logs_result_for_group_info(self):
        check_log_results = [
            CheckLogResult(result=True, severity=Severity.ERROR),
            CheckLogResult(result=True, severity=Severity.WARNING),
            CheckLogResult(result=False, severity=Severity.INFO),
        ]

        result = aggregate_check_logs_results_for_group(check_log_results=check_log_results)

        self.assertEqual(result, CheckLogResult(result=False, severity=Severity.INFO))

    def test_aggregate_check_logs_result_for_group_error(self):
        check_log_results = [
            CheckLogResult(result=False, severity=Severity.ERROR),
            CheckLogResult(result=False, severity=Severity.WARNING),
            CheckLogResult(result=False, severity=Severity.INFO),
        ]

        result = aggregate_check_logs_results_for_group(check_log_results=check_log_results)

        self.assertEqual(result, CheckLogResult(result=False, severity=Severity.ERROR))

    def test_aggregate_check_logs_result_for_group_default(self):
        check_log_results = [
            CheckLogResult(result=True, severity=Severity.ERROR),
            CheckLogResult(result=True, severity=Severity.WARNING),
            CheckLogResult(result=True, severity=Severity.INFO),
        ]

        result = aggregate_check_logs_results_for_group(check_log_results=check_log_results)

        self.assertEqual(result, CheckLogResult(result=True, severity=Severity.ERROR))
