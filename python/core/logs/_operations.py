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

from core.logs._constants import SEVERITY_PRIORITY
from core.logs._types import CheckLogResult


def aggregate_check_logs_results_for_group(check_log_results: list[CheckLogResult]) -> CheckLogResult:
    result = all(cl_result.result for cl_result in check_log_results)
    relevant_severity = sorted(
        (cl_result.severity for cl_result in check_log_results if not cl_result.result),
        key=lambda i: SEVERITY_PRIORITY[i],
    )
    all_severity = sorted((cl_result.severity for cl_result in check_log_results), key=lambda i: SEVERITY_PRIORITY[i])
    severity = relevant_severity[0] if relevant_severity else all_severity[0]

    return CheckLogResult(result=result, severity=severity)
