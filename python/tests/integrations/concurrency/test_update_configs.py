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

from collections.abc import Callable
from typing import Final

from ansible_plugin.executors.config import ADCMConfigPluginExecutor
from cm.models import Action, ADCMEntity, ConfigLog, Service
from core.action.job import LaunchOptions
from core.action.types import (
    ConfigApplyChangeEntry,
    ConfigApplyParameterEntry,
    ConfigApplyScript,
    ConfigApplyScriptParams,
    ScriptType,
    ServiceConfigApplyTarget,
)
from django.test import tag
from tests.integrations.concurrency.base import ConcurrencyBasicTestCase
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.concurrency.utils import (
    Branch,
    BranchCall,
    internal_script,
    plugin,
    prepare_config_branches_for_service,
    prepare_script_group,
)
from tests.integrations.constants import INTEGRATION_TESTS_TAG
from use_cases.dto import RunActionDTO
from use_cases.internal_scripts.config_apply import ConfigApplyInternalScript

# sync point after acquiring the configuration lock
CONFIG_UPDATE_SYNC_POINT = "core.config.ConfigService.retrieve_current_configuration"
PLUGIN_VALUE: Final = "from adcm_config"
INTERNAL_SCRIPT_VALUE: Final = "from config_apply"

BRANCH_COUNT = 10
# Ten branches update field_1 through field_10; field_11 verifies that untouched fields retain their initial value.
INITIAL_CONFIG = {f"field_{i}": "initial" for i in range(1, BRANCH_COUNT + 2)}


def change_config_by_plugin(key: str, service_name: str) -> Branch:
    return plugin(
        ADCMConfigPluginExecutor,
        {"type": "service", "service_name": service_name, "key": key, "value": PLUGIN_VALUE},
    )


def change_config_by_internal_script(key: str, service_name: str) -> Branch:
    change = ConfigApplyChangeEntry(
        object=ServiceConfigApplyTarget(type="service", service_name=service_name),
        parameters=[ConfigApplyParameterEntry(key=key, value=INTERNAL_SCRIPT_VALUE)],
    )
    return internal_script(
        ConfigApplyInternalScript,
        ConfigApplyScript(
            type=ScriptType.INTERNAL, path="config_apply", params=ConfigApplyScriptParams(changes=[change])
        ),
    )


@tag(INTEGRATION_TESTS_TAG)
class UpdateConfigsTestCase(ConcurrencyBasicTestCase):
    def prepare_changes(
        self, factory: Callable[[str, str], Branch], value: str
    ) -> tuple[tuple[BranchCall, ...], Service, dict[str, str]]:
        service, *_ = self.uc.add_services_to_cluster(["config_update_service"], cluster=self.cluster)
        branches, expected = prepare_config_branches_for_service(
            factory,
            value,
            branch_count=BRANCH_COUNT,
            initial_config=INITIAL_CONFIG,
            service_name=service.prototype.name,
        )
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="config_parallel")
        task = self.uc.schedule_task(
            action=action, target=self.cluster, payload=RunActionDTO(launch=LaunchOptions(is_blocking=False))
        )
        calls = prepare_script_group(task_id=task.pk, container=self.container, branches=branches)
        return calls, service, expected

    def get_config_history(self, target: ADCMEntity) -> list[ConfigLog]:
        return list(ConfigLog.objects.filter(obj_ref_id=target.config_id).order_by("id"))

    def assert_updates(self, factory: Callable[[str, str], Branch], value: str) -> None:
        calls, service, expected = self.prepare_changes(factory, value)

        synced_calls = [SyncedCall(func=call, sync_before=CONFIG_UPDATE_SYNC_POINT) for call in calls]
        outcomes = run_concurrently(*synced_calls)

        self.assert_errors_in_outcomes(outcomes, [])

        records = self.get_config_history(service)

        self.assert_config_count(service, BRANCH_COUNT + 1)
        # The initial configuration remains unchanged in history.
        self.assertEqual(records[0].config, INITIAL_CONFIG)
        # All parallel updates are preserved in the final configuration.
        self.assertEqual(records[-1].config, expected)
        # Current and previous point to the last two configuration versions.
        self.assertEqual(service.config.current, records[-1].pk)
        self.assertEqual(service.config.previous, records[-2].pk)

        self.assert_all_outcomes_synced_by_lock(outcomes)

    def test_adcm_config(self) -> None:
        self.assert_updates(change_config_by_plugin, PLUGIN_VALUE)

    def test_config_apply(self) -> None:
        self.assert_updates(change_config_by_internal_script, INTERNAL_SCRIPT_VALUE)
