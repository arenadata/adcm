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


from cm.models import Action, Service
from core.action.types import (
    ScriptType,
    ServiceManageScript,
    ServiceManageScriptParams,
    ServiceManageServiceEntry,
)
from django.test import tag
from pydantic import TypeAdapter
from tests.deprecated import LaunchOptions
from tests.integrations.concurrency.base import HOST_FQDN_1, HOST_FQDN_2, ConcurrencyBasicTestCase
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.concurrency.utils import internal_script, prepare_script_group
from tests.integrations.constants import INTEGRATION_TESTS_TAG
from use_cases.dto import RunActionDTO
from use_cases.internal_scripts.service_manage import ServiceManageInternalScript

SERVICE_MANAGE_SYNC_POINT = "use_cases.internal_scripts.service_manage.atomic"


@tag(INTEGRATION_TESTS_TAG)
class TestServiceManage(ConcurrencyBasicTestCase):
    def test_service_manage(self):
        action = Action.objects.get(prototype_id=self.cluster.prototype_id, name="jobs_for_branches")
        task = self.uc.schedule_task(
            action=action, target=self.cluster, payload=RunActionDTO(launch=LaunchOptions(is_blocking=False))
        )

        calls = [
            internal_script(
                ServiceManageInternalScript,
                script=ServiceManageScript(
                    type=ScriptType.INTERNAL,
                    path="service_manage",
                    params=ServiceManageScriptParams(
                        operation="add", services=TypeAdapter(list[ServiceManageServiceEntry]).validate_python(services)
                    ),
                ),
            )
            for services in (
                # CASE 1 - multi call with same config args -> ensure config isn't duplicated, no error
                [{"name": "service_1", "config_changes": [{"key": "first", "value": "cool"}]}],
                [{"name": "service_1", "config_changes": [{"key": "first", "value": "cool"}]}],
                [{"name": "service_1", "config_changes": [{"key": "first", "value": "cool"}]}],
                # CASE 2 - multi call with different mapping args
                #          -> ensure mapping is not broken, no error, only one host mapped
                [{"name": "service_2", "hc_changes": [{"component": "component_1", "hosts": [HOST_FQDN_1]}]}],
                [{"name": "service_2", "hc_changes": [{"component": "component_1", "hosts": [HOST_FQDN_2]}]}],
                [{"name": "service_2", "hc_changes": [{"component": "component_1", "hosts": [HOST_FQDN_1]}]}],
            )
        ]
        expected_mapping = [
            ("service_2", "component_1", 1),
        ]

        outcomes = run_concurrently(
            *(
                SyncedCall(call, sync_before=SERVICE_MANAGE_SYNC_POINT)
                for call in prepare_script_group(task.pk, container=self.container, branches=calls)
            )
        )

        succeed, errors = self.split_by_error(outcomes)
        self.assertEqual(len(errors), 0)
        self.assertEqual({out.result.code for out in succeed}, {0})

        service_1 = Service.objects.get(prototype__name="service_1", cluster_id=self.cluster.pk)
        service_2 = Service.objects.get(prototype__name="service_2", cluster_id=self.cluster.pk)
        self.assert_mapping(expected_mapping)
        # initial + new
        self.assert_config_count(service_1, 2)
        # initial
        self.assert_config_count(service_2, 1)
        self.assert_all_outcomes_synced_by_codepoint(outcomes)
