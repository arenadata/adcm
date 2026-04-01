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

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from cm.models import ADCMEntity, Bundle, ConfigLog, TaskLog
from django.db.models import Model

from rbac.models import re_apply_object_policy as legacy_re_apply_object_policy
from rbac.roles import (
    apply_policy_for_new_config as legacy_apply_policy_for_new_config,
)
from rbac.roles import (
    assign_view_logstorage_permissions_by_job as legacy_assign_view_logstorage_permissions_by_job,
)
from rbac.roles import (
    re_apply_policy_for_jobs as legacy_re_apply_policy_for_jobs,
)
from rbac.upgrade.role import prepare_action_roles as legacy_prepare_action_roles


@dataclass(slots=True)
class RBACScenarios:
    def re_apply_object_policy(
        self,
        apply_object: ADCMEntity,
        keep_objects: Mapping[type[Model], Iterable[int]] | None = None,
    ) -> None:
        legacy_re_apply_object_policy(
            apply_object=apply_object, keep_objects=dict(keep_objects) if keep_objects else None
        )

    def apply_policy_for_new_config(self, config_object: ADCMEntity, config_log: ConfigLog) -> None:
        legacy_apply_policy_for_new_config(config_object=config_object, config_log=config_log)

    def re_apply_policy_for_jobs(self, task: TaskLog) -> None:
        legacy_re_apply_policy_for_jobs(task=task)

    def assign_view_logstorage_permissions_by_job(self, log_storage_id: int) -> None:
        legacy_assign_view_logstorage_permissions_by_job(log_storage_id=log_storage_id)

    def prepare_action_roles(self, bundle: Bundle) -> None:
        legacy_prepare_action_roles(bundle=bundle)
