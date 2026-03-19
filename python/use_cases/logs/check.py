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

from core.logs import CheckLogArguments
from core.types import JobID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios
import core


@dataclass(slots=True)
class AddCheckLogRecordForJob:
    logs_service: core.logs.LogsService
    rbac_scenarios: RBACScenarios

    @atomic
    def do(self, job_id: JobID, check_log_arguments: CheckLogArguments):
        self.logs_service.add_check_log_for_job(job_id=job_id, check_log_arguments=check_log_arguments)
        log_storage_id, is_created = self.logs_service.add_log_storage_for_check_log(job_id=job_id)

        if is_created:
            self.rbac_scenarios.assign_view_logstorage_permissions_by_job(log_storage_id=log_storage_id)
