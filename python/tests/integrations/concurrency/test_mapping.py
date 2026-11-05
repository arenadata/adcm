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


from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from cm.models import Action, Component
from core.action.job import LaunchOptions
from core.action.types import HcAclRule, HcApplyScript, HcApplyScriptParams, ScriptType
from core.legacy.cluster.types import HostComponentEntry
from django.test import tag
from tests.integrations.concurrency.base import HOST_FQDN_1, HOST_FQDN_2, ConcurrencyBasicTestCase
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.concurrency.utils import internal_script, plugin, prepare_script_group
from tests.integrations.constants import INTEGRATION_TESTS_TAG
from use_cases.dto import RunActionDTO
from use_cases.internal_scripts.hc_apply import HcApplyInternalScript

ADCM_HC_SYNC_POINT = "ansible_plugin.executors.hostcomponent.get_hc"
HC_APPLY_SYNC_POINT = "use_cases.internal_scripts.hc_apply.atomic"


@tag(INTEGRATION_TESTS_TAG)
class TestMapping(ConcurrencyBasicTestCase):
    def setUp(self):
        super().setUp()
        self.uc.add_services_to_cluster(["service_1", "service_2"], cluster=self.cluster)

    def test_adcm_hc(self):
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="jobs_for_branches")
        task = self.uc.schedule_task(
            action=action, target=self.cluster, payload=RunActionDTO(launch=LaunchOptions(is_blocking=False))
        )

        # First batch adds hosts
        calls = [
            plugin(ADCMHostComponentPluginExecutor, {"operations": ops})
            for ops in (
                # CASE 1 - breaking constraint, expect one of calls to be an error
                [{"action": "add", "service": "service_1", "component": "component_1", "host": HOST_FQDN_1}],
                [{"action": "add", "service": "service_1", "component": "component_1", "host": HOST_FQDN_2}],
                # CASE 2 - adding independant host
                [{"action": "add", "service": "service_2", "component": "component_1", "host": HOST_FQDN_1}],
                # CASE 3 - adding already added host, expect fail
                [{"action": "add", "service": "service_2", "component": "component_1", "host": HOST_FQDN_1}],
            )
        ]
        expected_errors = [
            'Component "component_1" of service "service_1" has unsatisfied constraint: [0, 1]',
            'There is already component "component_1" on host "host-1"',
        ]
        expected_mapping = [
            ("service_1", "component_1", 1),
            ("service_2", "component_1", 1),
        ]

        outcomes = run_concurrently(
            *(
                SyncedCall(call, sync_before=ADCM_HC_SYNC_POINT)
                for call in prepare_script_group(task.pk, container=self.container, branches=calls)
            )
        )

        self.assert_errors_in_outcomes(outcomes, expected_errors)
        self.assert_mapping(expected_mapping)
        self.assert_all_outcomes_synced_by_lock(outcomes)

        # Second batch removes
        calls = [
            plugin(ADCMHostComponentPluginExecutor, {"operations": ops})
            for ops in (
                # CASE 4 - removing same entry - one will error
                [{"action": "remove", "service": "service_2", "component": "component_1", "host": HOST_FQDN_1}],
                [{"action": "remove", "service": "service_2", "component": "component_1", "host": HOST_FQDN_1}],
                # CASE 5 - removing non-existent entry
                #          (not including add-remove parallel case, because it's prone to race)
                [{"action": "remove", "service": "service_1", "component": "component_2", "host": HOST_FQDN_2}],
            )
        ]
        expected_errors = [
            'There is no component "component_1" on host ',
            'There is no component "component_2" on host ',
        ]
        expected_mapping = [
            ("service_1", "component_1", 1),
        ]

        outcomes = run_concurrently(
            *(
                SyncedCall(call, sync_before=ADCM_HC_SYNC_POINT)
                for call in prepare_script_group(task.pk, container=self.container, branches=calls)
            )
        )

        self.assert_errors_in_outcomes(outcomes, expected_errors)
        self.assert_mapping(expected_mapping)
        self.assert_all_outcomes_synced_by_lock(outcomes)

    def test_hc_apply(self):
        s1_c1 = Component.objects.get(
            cluster_id=self.cluster.pk, prototype__name="component_1", service__prototype__name="service_1"
        )
        s1_c2 = Component.objects.get(
            cluster_id=self.cluster.pk, prototype__name="component_2", service__prototype__name="service_1"
        )
        s2_c1 = Component.objects.get(
            cluster_id=self.cluster.pk, prototype__name="component_1", service__prototype__name="service_2"
        )

        mapping = {
            HostComponentEntry(host_id=host.pk, component_id=component.pk)
            for host, component in (
                (self.host_1, s1_c1),
                (self.host_1, s1_c2),
                (self.host_2, s1_c2),
                (self.host_1, s2_c1),
                (self.host_2, s2_c1),
            )
        }
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="jobs_for_branches_with_hc_acl")
        task = self.uc.schedule_task(
            action=action,
            target=self.cluster,
            payload=RunActionDTO(mapping=mapping, launch=LaunchOptions(is_blocking=False)),
        )

        # case
        calls = [
            internal_script(
                HcApplyInternalScript,
                script=HcApplyScript(
                    type=ScriptType.INTERNAL, path="hc_apply", params=HcApplyScriptParams(rules=rules)
                ),
            )
            for rules in (
                # CASE 1 apply 2 distinct sets of rules, leaving one of them "out"
                [HcAclRule(action="add", service="service_1", component="component_1")],
                [HcAclRule(action="add", service="service_2", component="component_1")],
                # CASE 2 duplicate one of statements - expect no error, just safe apply
                [HcAclRule(action="add", service="service_2", component="component_1")],
            )
        ]
        expected_errors = []
        expected_mapping = [
            ("service_1", "component_1", 1),
            ("service_2", "component_1", 2),
        ]

        outcomes = run_concurrently(
            *(
                SyncedCall(call, sync_before=HC_APPLY_SYNC_POINT)
                for call in prepare_script_group(task.pk, container=self.container, branches=calls)
            )
        )

        self.assert_errors_in_outcomes(outcomes, expected_errors)
        self.assert_mapping(expected_mapping)
        self.assert_all_outcomes_synced_by_codepoint(outcomes)
