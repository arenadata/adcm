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

from unittest.mock import patch

from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    JobLog,
    JobStatus,
    ObjectType,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.tests.mocks.task_runner import ExecutionTargetFactoryDummyMock, FailedJobInfo, RunTaskMock
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.tests.base import BaseAPITestCase


class TestTaskAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)
        self.cluster_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)[0]
        self.service_action = Action.objects.get(prototype=self.service.prototype, name="action")
        host = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_1)
        component_prototype = Prototype.objects.get(
            bundle=self.bundle_1, type=ObjectType.COMPONENT, name="component_1", parent=self.service.prototype
        )
        self.component = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service, prototype=component_prototype
        )
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(host, self.component)])
        self.component_action = Action.objects.get(prototype=self.component.prototype, name="action_1_comp_1")

    def simulate_finished_task(
        self, object_: Cluster | ClusterObject | ServiceComponent, action: Action
    ) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()

        return run_task.target_task, run_task.target_task.joblog_set.last()

    def simulate_running_task(
        self, object_: Cluster | ClusterObject | ServiceComponent, action: Action
    ) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()
        task = run_task.target_task
        job = task.joblog_set.last()
        task.status = JobStatus.RUNNING
        task.save(update_fields=["status"])
        job.status = JobStatus.RUNNING
        job.pid = 5_000_000
        job.save(update_fields=["status", "pid"])

        return task, job

    def test_run_action_success(self):
        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

        run_task.run()

        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} action completed",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=None,
        )

    def test_run_action_fail(self):
        with RunTaskMock(
            execution_target_factory=ExecutionTargetFactoryDummyMock(
                failed_job=FailedJobInfo(position=0, return_code=1)
            )
        ) as run_task:
            response = (self.client.v2[self.service] / "actions" / self.service_action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_record(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service),
            user__username="admin",
        )

        run_task.run()

        self.check_last_audit_record(
            operation_name=f"{self.service_action.display_name} action completed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service),
            user__username=None,
        )

    def test_run_not_exists_action_fail(self):
        with RunTaskMock() as run_task:
            response = (self.client.v2[self.component] / "actions" / self.get_non_existent_pk(Action) / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertIsNone(run_task.target_task)
        self.check_last_audit_record(
            operation_name="action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component),
            user__username="admin",
        )

    def test_run_action_denied(self):
        self.client.login(**self.test_user_credentials)
        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertIsNone(run_task.target_task)
        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="test_user_username",
        )

    def test_terminate_job_success(self):
        task, job = self.simulate_running_task(object_=self.cluster_1, action=self.cluster_action)

        with patch("cm.models.os.kill"):
            response = self.client.v2[job, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} terminated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_terminate_job_not_found_fail(self):
        self.simulate_running_task(object_=self.service, action=self.service_action)

        with patch("cm.models.os.kill"):
            response = (self.client.v2 / "jobs" / self.get_non_existent_pk(JobLog) / "terminate").post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="fail",
                **self.prepare_audit_object_arguments(expected_object=None),
                user__username="admin",
            )

    def test_terminate_job_denied(self):
        # TODO: This test discovered an issue with creating a new audit object, this needs to be fixed
        _, job = self.simulate_running_task(object_=self.component, action=self.component_action)
        self.client.login(**self.test_user_credentials)

        with patch("cm.models.os.kill"):
            response = self.client.v2[job, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name=f"{self.component_action.display_name} terminated",
                operation_type="update",
                operation_result="denied",
                audit_object__object_id=self.component.id,
                audit_object__object_name="component_1",  # TODO: should be "cluster_1/service_1/component_1"
                audit_object__object_type="service component",  # TODO: should be "component"
                audit_object__is_deleted=False,
                user__username="test_user_username",
            )

    def test_terminate_task_success(self):
        task, _ = self.simulate_running_task(object_=self.cluster_1, action=self.cluster_action)

        with patch("cm.models.os.kill"):
            response = self.client.v2[task, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.check_last_audit_record(
                operation_name=f"{self.cluster_action.display_name} cancelled",
                operation_type="update",
                operation_result="success",
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
                user__username="admin",
            )

    def test_terminate_task_not_found_fail(self):
        self.simulate_running_task(object_=self.service, action=self.service_action)

        with patch("cm.models.os.kill"):
            response = (self.client.v2 / "tasks" / self.get_non_existent_pk(TaskLog) / "terminate").post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="fail",
                audit_object__isnull=True,
                user__username="admin",
            )

    def test_terminate_task_denied(self):
        # TODO: This test discovered an issue with creating a new audit object, this needs to be fixed
        task, _ = self.simulate_running_task(object_=self.component, action=self.component_action)
        self.client.login(**self.test_user_credentials)

        with patch("cm.models.os.kill"):
            response = self.client.v2[task, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name=f"{self.component_action.display_name} cancelled",
                operation_type="update",
                operation_result="denied",
                audit_object__object_id=self.component.id,
                audit_object__object_name="component_1",  # TODO: should be "cluster_1/service_1/component_1"
                audit_object__object_type="service component",  # TODO should be "component"
                user__username="test_user_username",
            )

    def test_terminate_finished_job_fail(self):
        task, job = self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_action)

        with patch("cm.models.os.kill"):
            response = self.client.v2[job, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} terminated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_terminate_finished_task_fail(self):
        # TODO: This test discovered an issue with creating a new audit object, this needs to be fixed
        task, _ = self.simulate_finished_task(object_=self.service, action=self.service_action)

        with patch("cm.models.os.kill"):
            response = self.client.v2[task, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            self.check_last_audit_record(
                operation_name=f"{self.service_action.display_name} cancelled",
                operation_type="update",
                operation_result="fail",
                audit_object__object_id=self.service.id,
                audit_object__object_name="service_1",  # TODO: should be "cluster_1/service_1"
                audit_object__object_type="cluster object",  # TODO: should be "service"
                audit_object__is_deleted=False,
                user__username="admin",
            )

    def test_terminate_finished_job_after_delete_object_fail(self):
        _, job = self.simulate_finished_task(object_=self.component, action=self.component_action)

        response = self.client.v2[self.cluster_1].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        with patch("cm.models.os.kill"):
            response = self.client.v2[job, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name=f"{self.component_action.display_name} terminated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_terminate_finished_task_after_delete_object_fail(self):
        task, _ = self.simulate_finished_task(object_=self.component, action=self.component_action)

        response = self.client.v2[self.cluster_1].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        with patch("cm.models.os.kill"):
            response = self.client.v2[task, "terminate"].post(data={})
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            self.check_last_audit_record(
                operation_name=f"{self.component_action.display_name} cancelled",
                operation_type="update",
                operation_result="fail",
                **self.prepare_audit_object_arguments(expected_object=None),
                user__username="admin",
            )
