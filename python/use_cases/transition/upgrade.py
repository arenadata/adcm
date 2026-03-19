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

from typing import Literal

from cm import models
from cm.errors import AdcmEx
from cm.legacy.api import check_license
from cm.legacy.bundle_switch_revert import bundle_switch
from cm.legacy.status_api import send_prototype_and_state_update_event

# todo waiting for refactoring, don't want to copy it anywhere for now
from cm.legacy.upgrade import check_upgrade, update_before_upgrade
from core.types import TaskID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios
import core

from use_cases.dto import UpgradeActionDTO
from use_cases.legacy.upgrade import build_switch_revert_callbacks
from use_cases.transition.job.schedule import ScheduleTask


def upgrade_object(
    obj: models.Cluster | models.Provider,
    upgrade: models.Upgrade,
    *,
    payload: UpgradeActionDTO,
    schedule_task: ScheduleTask,
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
) -> tuple[Literal["plain"], None] | tuple[Literal["task"], TaskID]:
    with atomic():
        check_license(prototype=obj.prototype)
        upgrade_prototype = models.Prototype.objects.get(
            bundle=upgrade.bundle,
            name=upgrade.bundle.name,
            type__in=(models.ObjectType.CLUSTER, models.ObjectType.PROVIDER),
        )
        check_license(prototype=upgrade_prototype)

        success, msg = check_upgrade(obj=obj, upgrade=upgrade)
        if not success:
            raise AdcmEx(code="UPGRADE_ERROR", msg=msg)

        obj.before_upgrade["bundle_id"] = obj.prototype.bundle.pk
        update_before_upgrade(obj=obj)

        if not upgrade.action:
            callbacks = build_switch_revert_callbacks(config_service=config_service, rbac_scenarios=rbac_scenarios)
            bundle_switch(obj=obj, upgrade=upgrade, callbacks=callbacks, config_service=config_service)

            if upgrade.state_on_success:
                obj.state = upgrade.state_on_success
                obj.save(update_fields=["state"])

            send_prototype_and_state_update_event(object_=obj)
            return "plain", None

        task = schedule_task.do(action_orm=upgrade.action, target=obj, payload=payload.to_run_action_dto())

        return "task", task.pk
