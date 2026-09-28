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

from datetime import timedelta
from pathlib import Path
from typing import Final

from cm.models import ADCM, Action, JobLog, TaskLog
from core import secrets
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rbac.models import User
from rbac.scenarios import RBACScenarios
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from tests.base import WithPreparedFSAndInitADCM
from tests.client import ADCMTestClient
from tests.dependencies import get_status_scenarios_manager
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuite, ADCMDjangoAPISuiteNoBundles
from use_cases.dto import RunActionDTO
from use_cases.transition.job.schedule import ScheduleTask
import dishka
import django.test


class TestStatusServerSync(django.test.TestCase, WithPreparedFSAndInitADCM):
    client: ADCMTestClient
    client_class = ADCMTestClient

    def get_sync_endpoint(self):
        return self.client.v2 / "internal" / "unstable" / "status-server" / "sync"

    def setUp(self) -> None:
        get_status_scenarios_manager().reset()

    def test_authorized_user_call_sync(self):
        status_user = User.objects.get(username="status")

        self.client.force_authenticate(status_user)

        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        get_status_scenarios_manager().expect_called_once("update_all")

    def test_no_user_call_sync(self):
        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        get_status_scenarios_manager().expect_not_called("update_all")

    def test_unauthorized_user_call_sync(self):
        admin_user = User.objects.get(username="admin")

        self.client.force_authenticate(admin_user)

        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        get_status_scenarios_manager().expect_not_called("update_all")


class TestStatusServerGetToken(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def get_token_endpoint(self):
        return self.client.v2 / "internal" / "unstable" / "status-server" / "get-token"

    def test_superuser_success(self):
        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        with self.container(scope=dishka.Scope.REQUEST) as container:
            expected_token = container.get(secrets.StatusCheckerStatusServiceToken)
        self.assertEqual(response.json(), {"token": expected_token})

    def test_regular_user_forbidden(self):
        self.client.login(**self.test_user_credentials)

        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        self.client.logout()

        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_post_not_allowed(self):
        response = self.get_token_endpoint().post()

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)


BUNDLE_DIR: Final = Path(__file__).parent / "bundles" / "execution_plan"

# anchor for runtime dates simulated directly in the DB, offsets mirror `response-example.json`
BASE_TIME: Final = timezone.now()


def at(seconds: int):
    return BASE_TIME + timedelta(seconds=seconds)


def iter_job_nodes(nodes: list[dict]):
    """Flatten an execution plan's `children` tree down to its job nodes, depth-first"""

    for node in nodes:
        if node["kind"] == "job":
            yield node
        else:
            yield from iter_job_nodes(node["children"])


class TestTaskExecutionPlan(ADCMDjangoAPISuiteNoBundles):
    # real RBAC processing (bundle-upload action roles, task-launch policy re-application) is needed
    # for API-10/API-11's permission checks; the default "minimal" setup stubs it out for speed
    suite_setup = SETUP_WITH_RBAC

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        bundle = cls.uc.upload_bundle(src=BUNDLE_DIR)
        cls.cluster = cls.uc.add_cluster(bundle=bundle, name="Execution Plan Cluster")

        grouped_action = Action.objects.get(prototype=cls.cluster.prototype, name="grouped")
        flat_action = Action.objects.get(prototype=cls.cluster.prototype, name="flat")

        cls.grouped_task = cls.launch_action(grouped_action)
        cls.flat_task = cls.launch_action(flat_action)

    @classmethod
    def launch_action(cls, action: Action) -> TaskLog:
        """Runs an action the same way the `run` endpoint does, without going through the request layer"""

        with cls.container(scope=dishka.Scope.REQUEST) as request_container:
            return request_container.get(ScheduleTask).do(action_orm=action, target=cls.cluster, payload=RunActionDTO())

    def execution_plan_endpoint(self, task: TaskLog | int):
        return self.client.v2 / "internal" / "unstable" / "tasks" / task / "execution-plan"

    @staticmethod
    def set_job(task: TaskLog, name: str, status: str, start=None, finish=None) -> None:
        JobLog.objects.filter(task=task, name=name).update(status=status, start_date=start, finish_date=finish)

    @staticmethod
    def set_task_status(task: TaskLog, status: str) -> None:
        TaskLog.objects.filter(id=task.pk).update(status=status)

    def test_fresh_task_returns_full_tree_all_created(self) -> None:
        response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["version"], 1)
        self.assertNotIn("executionEnvironment", data)

        pre_check, shards, finalize = data["children"]

        self.assertEqual(
            pre_check,
            {
                "kind": "job",
                "id": pre_check["id"],
                "name": "pre_check",
                "displayName": "Pre-check",
                "status": "created",
                "startTime": None,
                "endTime": None,
                "duration": None,
                "isTerminatable": True,
            },
        )

        self.assertEqual((shards["kind"], shards["status"]), ("parallel", "created"))
        self.assertIsNone(shards["startTime"])
        self.assertIsNone(shards["endTime"])
        self.assertIsNone(shards["duration"])
        self.assertTrue(shards["isTerminatable"])

        shard_a, shard_b = shards["children"]
        self.assertEqual((shard_a["kind"], shard_a["status"]), ("sequential", "created"))
        self.assertEqual([job["name"] for job in shard_a["children"]], ["stop_a", "reconfigure_a", "start_a"])
        self.assertEqual((shard_b["kind"], shard_b["status"]), ("sequential", "created"))
        self.assertEqual([job["name"] for job in shard_b["children"]], ["stop_b", "reconfigure_b", "start_b"])

        self.assertEqual((finalize["name"], finalize["status"]), ("finalize", "created"))

    def test_mixed_runtime_matches_example_state(self) -> None:
        self.set_job(self.grouped_task, "pre_check", "success", at(0), at(12))
        self.set_job(self.grouped_task, "stop_a", "success", at(12), at(30))
        self.set_job(self.grouped_task, "reconfigure_a", "success", at(30), at(60))
        self.set_job(self.grouped_task, "start_a", "success", at(60), at(77))
        self.set_job(self.grouped_task, "stop_b", "success", at(14), at(40))
        self.set_job(self.grouped_task, "reconfigure_b", "running", at(40), None)
        self.set_task_status(self.grouped_task, "running")

        response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        pre_check, shards, finalize = response.json()["children"]

        self.assertEqual(pre_check["status"], "success")
        self.assertEqual(pre_check["duration"], 12)

        self.assertEqual(shards["status"], "running")
        self.assertIsNone(shards["endTime"])
        self.assertIsNone(shards["duration"])

        shard_a, shard_b = shards["children"]
        self.assertEqual(shard_a["status"], "success")
        self.assertEqual(shard_a["duration"], 65)

        self.assertEqual(shard_b["status"], "running")
        self.assertIsNone(shard_b["endTime"])

        self.assertEqual(finalize["status"], "created")

    def test_finished_failed_task_stopped_branch_is_running(self) -> None:
        self.set_job(self.grouped_task, "pre_check", "success", at(0), at(12))
        self.set_job(self.grouped_task, "stop_a", "success", at(12), at(20))
        self.set_job(self.grouped_task, "reconfigure_a", "success", at(20), at(30))
        # start_a never ran: the branch reads as `running` even though the task is finished
        self.set_job(self.grouped_task, "stop_b", "success", at(12), at(20))
        self.set_job(self.grouped_task, "reconfigure_b", "failed", at(20), at(25))
        self.set_task_status(self.grouped_task, "failed")

        response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        _, shards, _ = response.json()["children"]
        shard_a, shard_b = shards["children"]

        self.assertEqual(shard_a["status"], "running")
        self.assertIsNone(shard_a["endTime"])
        self.assertEqual(shard_b["status"], "failed")
        # a running child wins over a failed one
        self.assertEqual(shards["status"], "running")

    def test_flat_action_has_job_nodes_only(self) -> None:
        response = self.execution_plan_endpoint(self.flat_task).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        children = response.json()["children"]

        self.assertEqual([node["kind"] for node in children], ["job", "job"])
        self.assertEqual([node["name"] for node in children], ["first", "second"])

    def test_job_node_fields_match_child_jobs_entry(self) -> None:
        self.set_job(self.grouped_task, "pre_check", "success", at(0), at(12))
        self.set_job(self.grouped_task, "stop_a", "running", at(12), None)
        self.set_task_status(self.grouped_task, "running")

        plan_response = self.execution_plan_endpoint(self.grouped_task).get()
        task_response = self.client.v2[self.grouped_task].get()

        self.assertEqual(plan_response.status_code, HTTP_200_OK)
        self.assertEqual(task_response.status_code, HTTP_200_OK)

        child_jobs_by_id = {job["id"]: job for job in task_response.json()["childJobs"]}
        job_nodes = list(iter_job_nodes(plan_response.json()["children"]))

        self.assertEqual({node["id"] for node in job_nodes}, set(child_jobs_by_id))
        for node in job_nodes:
            expected = child_jobs_by_id[node["id"]]
            self.assertEqual(
                node,
                {
                    "kind": "job",
                    "id": expected["id"],
                    "name": expected["name"],
                    "displayName": expected["displayName"],
                    "status": expected["status"],
                    "startTime": expected["startTime"],
                    "endTime": expected["endTime"],
                    "duration": expected["duration"],
                    "isTerminatable": expected["isTerminatable"],
                },
            )

    def test_legacy_task_without_stored_plan_is_not_found(self) -> None:
        TaskLog.objects.filter(id=self.flat_task.pk).update(execution_plan=None)

        response = self.execution_plan_endpoint(self.flat_task).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_non_existent_task_is_not_found(self) -> None:
        response = self.execution_plan_endpoint(self.get_non_existent_pk(TaskLog)).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_unauthenticated_is_unauthorized(self) -> None:
        self.client.logout()

        response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_user_without_view_permission_is_not_found(self) -> None:
        credentials = {"username": "no_perms_user", "password": "no_perms_password"}
        self.uc.create_user(**credentials)
        self.client.login(**credentials)

        response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_permitted_non_superuser_gets_200(self) -> None:
        credentials = {"username": "cluster_admin_user", "password": "cluster_admin_passwo"}
        user = self.uc.create_user(**credentials)

        with self.grant_permissions(to=user, on=self.cluster, role_name="Cluster Administrator"):
            # the task was launched (in `setUpTestData`) before this policy existed to see it,
            # so object permissions on it need a manual refresh -- same as a real re-launch would trigger
            self.container.get(RBACScenarios).re_apply_policy_for_jobs(task=self.grouped_task)

            self.client.login(**credentials)
            response = self.execution_plan_endpoint(self.grouped_task).get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_owned_task_is_not_found_for_non_superuser(self) -> None:
        adcm_task = TaskLog.objects.create(
            object_id=ADCM.objects.first().pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            status="created",
        )

        credentials = {"username": "plain_user", "password": "plain_user_password"}
        self.uc.create_user(**credentials)
        self.client.login(**credentials)

        response = self.execution_plan_endpoint(adcm_task).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_plan_job_mismatch_raises(self) -> None:
        JobLog.objects.filter(task=self.flat_task, name="first").update(spec_key="/does-not-exist")

        with self.assertRaises(KeyError):
            self.execution_plan_endpoint(self.flat_task).get()
