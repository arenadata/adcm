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

"""
Examples of concurrency scenarios: branches are run in parallel and one by one.

Branches of a scenario are declared right here as plain calls (see `utils`):
plugin executor with its arguments (e.g. `ADCMConfigPluginExecutor` with what `adcm_config` gets in playbook)
or internal script with its params (e.g. `ConfigApplyInternalScript` with `ConfigApplyScript`).
Task of `jobs_for_branches*` action is only created via API to give branches the task and their jobs,
task runner isn't involved. Parallel branches are run via `run_concurrently`, sequential ones one by one.
Errors of plugins and scripts are raised by calls, so `run_concurrently` returns them as outcomes' errors.

Only that branches are run without errors is checked, outcomes of scenarios are checked by tests of their fixes:
synchronization at the start of branches doesn't guarantee that race happens.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ansible_plugin.executors.config import ADCMConfigPluginExecutor
from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from ansible_plugin.executors.multi_state_set import ADCMMultiStateSetPluginExecutor
from ansible_plugin.executors.state import ADCMStatePluginExecutor
from cm.models import Action, Cluster, Component, Host
from core.action.types import (
    ConfigApplyChangeEntry,
    ConfigApplyParameterEntry,
    ConfigApplyScript,
    ConfigApplyScriptParams,
    HcAclRule,
    HcApplyScript,
    HcApplyScriptParams,
    ScriptType,
    ServiceConfigApplyTarget,
    ServiceManageConfigChange,
    ServiceManageScript,
    ServiceManageScriptParams,
    ServiceManageServiceEntry,
    SimpleInternalScript,
    TypeBasedConfigApplyTarget,
)
from core.types import TaskID
from django.test import tag
from rest_framework.status import HTTP_200_OK
from tests.client import ADCMTestClient
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.concurrency.utils import (
    BRANCH_START,
    Branch,
    BranchCall,
    internal_script,
    plugin,
    prepare_script_group,
)
from tests.integrations.constants import INTEGRATION_TESTS_TAG
from tests.suites import GenericTransactionTestCase
from unittest_parametrize import ParametrizedTestCase, param, parametrize
from use_cases.internal_scripts.before_upgrade_clean import BeforeUpgradeCleanInternalScript
from use_cases.internal_scripts.config_apply import ConfigApplyInternalScript
from use_cases.internal_scripts.hc_apply import HcApplyInternalScript
from use_cases.internal_scripts.service_manage import ServiceManageInternalScript

BUNDLES_DIR: Final = Path(__file__).parent / "bundles"

HOST_FQDN: Final = "host-1"

# actions whose tasks give branches their jobs
JOBS_ACTION: Final = "jobs_for_branches"
JOBS_WITH_HC_ACL_ACTION: Final = "jobs_for_branches_with_hc_acl"
JOBS_THREE_ACTION: Final = "jobs_for_branches_three"

PLUGIN_VALUE: Final = "from adcm_config"
INTERNAL_SCRIPT_VALUE: Final = "from config_apply"
SERVICE_MANAGE_VALUE: Final = "from service_manage"

RUN_ACTION_PAYLOAD: Final = {"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}


def set_multi_state(state: str) -> Branch:
    return plugin(ADCMMultiStateSetPluginExecutor, {"type": "cluster", "state": state})


def set_state(state: str) -> Branch:
    return plugin(ADCMStatePluginExecutor, {"type": "cluster", "state": state})


def clean_before_upgrade() -> Branch:
    return internal_script(
        BeforeUpgradeCleanInternalScript,
        SimpleInternalScript(type=ScriptType.INTERNAL, path="before_upgrade_clean", params=None),
    )


def change_config_by_plugin(key: str, service_name: str | None = None) -> Branch:
    target = {"type": "service", "service_name": service_name} if service_name else {"type": "cluster"}

    return plugin(ADCMConfigPluginExecutor, {**target, "key": key, "value": PLUGIN_VALUE})


def change_config_by_internal_script(key: str, service_name: str | None = None) -> Branch:
    target = (
        ServiceConfigApplyTarget(type="service", service_name=service_name)
        if service_name
        else TypeBasedConfigApplyTarget(type="cluster")
    )
    change = ConfigApplyChangeEntry(
        object=target, parameters=[ConfigApplyParameterEntry(key=key, value=INTERNAL_SCRIPT_VALUE)]
    )

    return internal_script(
        ConfigApplyInternalScript,
        ConfigApplyScript(
            type=ScriptType.INTERNAL, path="config_apply", params=ConfigApplyScriptParams(changes=[change])
        ),
    )


def map_component_by_plugin(service_name: str) -> Branch:
    operation = {"action": "add", "service": service_name, "component": "component_1", "host": HOST_FQDN}

    return plugin(ADCMHostComponentPluginExecutor, {"operations": [operation]})


def map_component_by_internal_script(service_name: str) -> Branch:
    """Applies its part of mapping passed on action's run"""

    rule = HcAclRule(service=service_name, component="component_1", action="add")

    return internal_script(
        HcApplyInternalScript,
        HcApplyScript(type=ScriptType.INTERNAL, path="hc_apply", params=HcApplyScriptParams(rules=[rule])),
    )


def add_service(name: str) -> Branch:
    service = ServiceManageServiceEntry(
        name=name, config_changes=[ServiceManageConfigChange(key="first", value=SERVICE_MANAGE_VALUE)], hc_changes=None
    )

    return internal_script(
        ServiceManageInternalScript,
        ServiceManageScript(
            type=ScriptType.INTERNAL,
            path="service_manage",
            params=ServiceManageScriptParams(operation="add", services=[service]),
        ),
    )


@dataclass(frozen=True, slots=True)
class Scenario:
    branches: tuple[Branch, ...]
    jobs_action: str = JOBS_ACTION


SCENARIOS: Final = {
    # different multi-states of the cluster
    "multi_state_set_twice": Scenario(branches=(set_multi_state("first"), set_multi_state("second"))),
    # multi-state and state of the cluster
    "multi_state_set_and_state": Scenario(branches=(set_multi_state("first"), set_state("changed"))),
    # different keys of cluster's config
    "config_keys_plugin": Scenario(branches=(change_config_by_plugin("first"), change_config_by_plugin("second"))),
    "config_keys_internal": Scenario(
        branches=(change_config_by_internal_script("first"), change_config_by_internal_script("second"))
    ),
    "config_keys_mixed": Scenario(
        branches=(change_config_by_plugin("first"), change_config_by_internal_script("second"))
    ),
    # configs of cluster and `service_1`
    "config_objects_plugin": Scenario(
        branches=(change_config_by_plugin("first"), change_config_by_plugin("first", service_name="service_1"))
    ),
    "config_objects_internal": Scenario(
        branches=(
            change_config_by_internal_script("first"),
            change_config_by_internal_script("first", service_name="service_1"),
        )
    ),
    "config_objects_mixed": Scenario(
        branches=(
            change_config_by_plugin("first"),
            change_config_by_internal_script("first", service_name="service_1"),
        )
    ),
    # components of different services are mapped to the host
    "hc_plugin": Scenario(branches=(map_component_by_plugin("service_1"), map_component_by_plugin("service_2"))),
    "hc_internal": Scenario(
        branches=(map_component_by_internal_script("service_1"), map_component_by_internal_script("service_2")),
        jobs_action=JOBS_WITH_HC_ACL_ACTION,
    ),
    # different services are added with config changes
    "service_manage": Scenario(branches=(add_service("service_3"), add_service("service_4"))),
    # `before_upgrade_clean` runs alongside state and multi-state changes of the cluster
    "before_upgrade_clean_with_state_and_multi_state": Scenario(
        branches=(clean_before_upgrade(), set_multi_state("first"), set_state("changed")),
        jobs_action=JOBS_THREE_ACTION,
    ),
}
SCENARIO_PARAMS: Final = [param(scenario, id=scenario) for scenario in SCENARIOS]


class BaseScenarioTestCase(GenericTransactionTestCase):
    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient
    # errors of branches are compared as is, their messages shouldn't be cut
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        self._initialize_roles_and_adcm()
        self.cluster, self.host = self.prepare_environment()
        self.client.login(username="admin", password="admin")

    def prepare_environment(self) -> tuple[Cluster, Host]:
        """Objects scenarios expect (see cluster bundle)"""

        cluster_bundle = self.uc.upload_bundle(BUNDLES_DIR / "cluster")
        provider_bundle = self.uc.upload_bundle(BUNDLES_DIR / "provider")

        cluster = self.uc.add_cluster(bundle=cluster_bundle, name="Concurrency cluster")
        self.uc.add_services_to_cluster(["service_1", "service_2"], cluster=cluster)

        provider = self.uc.add_provider(bundle=provider_bundle, name="Concurrency provider")
        host = self.uc.add_host(provider=provider, fqdn=HOST_FQDN, cluster=cluster)

        return cluster, host

    def start_action(self, name: str) -> TaskID:
        """Create task of cluster's action via API, task isn't launched"""

        action = Action.objects.get(prototype=self.cluster.prototype, name=name)

        mapping = []
        if action.hostcomponentmap:
            # every component of `hc_acl` is mapped to the host
            mapping = [
                {"hostId": self.host.id, "componentId": component_id}
                for component_id in Component.objects.filter(
                    cluster=self.cluster, prototype__name="component_1"
                ).values_list("id", flat=True)
            ]

        payload = {**RUN_ACTION_PAYLOAD, "hostComponentMap": mapping}
        response = self.client.v2[self.cluster, "actions", action, "run"].post(data=payload)
        if response.status_code != HTTP_200_OK:
            message = f"Action {name} isn't started: {response.status_code} {response.json()}"
            raise AssertionError(message)

        return response.json()["id"]

    def prepare_script_group(self, scenario: str) -> tuple[BranchCall, ...]:
        definition = SCENARIOS[scenario]
        task_id = self.start_action(definition.jobs_action)

        return prepare_script_group(task_id=task_id, container=self.container, branches=definition.branches)


@tag(INTEGRATION_TESTS_TAG)
class TestScenarioBranches(ParametrizedTestCase, BaseScenarioTestCase):
    @staticmethod
    def call_and_catch(call: BranchCall) -> Exception | None:
        """Error of the call, so it's reported the same way as errors of `run_concurrently`"""

        try:
            call()
        except Exception as e:  # noqa: BLE001
            return e

        return None

    @parametrize("scenario", SCENARIO_PARAMS)
    def test_parallel_branches_run_concurrently_success(self, scenario: str) -> None:
        script_group = self.prepare_script_group(scenario)

        outcomes = run_concurrently(*(SyncedCall(func=call, sync_before=BRANCH_START) for call in script_group))

        self.assertEqual(
            [(outcome.error, outcome.synchronized) for outcome in outcomes], [(None, True)] * len(script_group)
        )

    @parametrize("scenario", SCENARIO_PARAMS)
    def test_sequential_branches_run_one_by_one_success(self, scenario: str) -> None:
        script_group = self.prepare_script_group(scenario)

        self.assertEqual([self.call_and_catch(call) for call in script_group], [None] * len(script_group))
