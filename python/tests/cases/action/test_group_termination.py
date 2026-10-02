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
API-level coverage of `JobService.terminate_group` and the optional group-termination
body of `POST /api/v2/tasks/{id}/terminate/`.

Task and jobs are created via the API and left in `CREATED` (the task runner is never
launched), then nudged into whatever statuses a case needs directly through the ORM --
same style as `test_local_task_run.py` and `test_script_groups.py`.

Every request is followed by an audit check of the last record:
a named group is recorded by its display name (fixture display names differ from internal ones),
a body without `group` is recorded as task termination.
"""

from pathlib import Path
from typing import Any, Final

from cm.impl.job.repo import JobRepo
from cm.models import Action, Cluster, JobLog, TaskLog
from core.action import ExecutionStatus
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from unittest_parametrize import param, parametrize

from tests.client import APINode
from tests.suites import ADCMDjangoAPISuiteNoBundles

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "group_termination"

RUN_ACTION_PAYLOAD: Final = {"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}

# spec keys of `grouped`/`grouped_not_terminatable`, both built from the same plan shape:
# prepare, group `a` (parallel, display "Group A") with its own script and sequential
# subgroup `nested` (display "Nested Of A", 2 scripts), group `ab` (sequential, display "Group AB", 1 script), finish
PREPARE: Final = "/0"
A_OWN: Final = "/a/0"
NESTED_0: Final = "/a/nested/0"
NESTED_1: Final = "/a/nested/1"
AB_0: Final = "/ab/0"
FINISH: Final = "/3"

ALL_KEYS: Final = (PREPARE, A_OWN, NESTED_0, NESTED_1, AB_0, FINISH)

CREATED: Final = ExecutionStatus.CREATED
RUNNING: Final = ExecutionStatus.RUNNING
SUCCESS: Final = ExecutionStatus.SUCCESS
FAILED: Final = ExecutionStatus.FAILED
ABORTED: Final = ExecutionStatus.ABORTED
REVOKED: Final = ExecutionStatus.REVOKED
REVOKING: Final = ExecutionStatus.REVOKING
TERMINATING: Final = ExecutionStatus.TERMINATING

ALL_CREATED: Final = dict.fromkeys(ALL_KEYS, CREATED)

GROUP_DISPLAY_NAMES: Final = {"a": "Group A", "nested": "Nested Of A", "ab": "Group AB"}

# spec keys of `named_groups`: one script in each of groups `5`, `braced`, `long`
FIVE_0: Final = "/5/0"
BRACED_0: Final = "/braced/0"
LONG_0: Final = "/long/0"

NAMED_GROUPS_ALL_CREATED: Final = dict.fromkeys((FIVE_0, BRACED_0, LONG_0), CREATED)


class TestGroupTermination(ADCMDjangoAPISuiteNoBundles):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster")
        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Group Termination")

    # -- helpers --

    def run_action(self, action_name: str) -> int:
        action = Action.objects.get(prototype=self.cluster.prototype, name=action_name)

        response = self.client.v2[self.cluster, "actions", action, "run"].post(data=RUN_ACTION_PAYLOAD)
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

        return response.json()["id"]

    def set_job_status(self, task_id: int, key: str, status: ExecutionStatus) -> None:
        updated = JobLog.objects.filter(task_id=task_id, spec_key=key).update(status=status.value)
        self.assertEqual(updated, 1, f"job {key!r} of task #{task_id} not found")

    def set_task_status(self, task_id: int, status: ExecutionStatus) -> None:
        updated = TaskLog.objects.filter(id=task_id).update(status=status.value)
        self.assertEqual(updated, 1, f"task #{task_id} not found")

    def terminate_node(self, task_id: int) -> APINode:
        return self.client.v2 / "tasks" / task_id / "terminate"

    def terminate(self, task_id: int, data: dict | list | None) -> Response:
        node = self.terminate_node(task_id)

        return node.post(data=data) if data is not None else node.post()

    def assert_jobs(self, task_id: int, expected: dict[str, ExecutionStatus]) -> None:
        actual = {job.spec_key: ExecutionStatus(job.status) for job in JobLog.objects.filter(task_id=task_id)}
        self.assertDictEqual(actual, expected)

    def assert_task_status(self, task_id: int, expected: ExecutionStatus) -> None:
        self.assertEqual(ExecutionStatus(TaskLog.objects.values_list("status", flat=True).get(id=task_id)), expected)

    def assert_audit(self, name: str, result: str, object_: Cluster | None, username: str = "admin") -> None:
        self.check_last_audit_record(
            operation_name=name,
            operation_type="update",
            operation_result=result,
            **self.prepare_audit_object_arguments(expected_object=object_),
            user__username=username,
        )

    def action_display_name(self, action_name: str) -> str:
        return Action.objects.get(prototype=self.cluster.prototype, name=action_name).display_name

    # -- S1: group not started, 1- and 2-level --

    @parametrize(
        "group_name,expected_changed",
        [
            param("ab", {AB_0: REVOKED}, id="one_level"),
            param("a", {A_OWN: REVOKED, NESTED_0: REVOKED, NESTED_1: REVOKED}, id="two_level"),
        ],
    )
    def test_terminate_unstarted_group_success(self, group_name: str, expected_changed: dict[str, ExecutionStatus]):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, {"group": group_name})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(task_id, ALL_CREATED | expected_changed)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "{GROUP_DISPLAY_NAMES[group_name]}" cancelled',
            result="success",
            object_=self.cluster,
        )

    # -- S2: parallel group, mixed statuses --

    def test_terminate_parallel_group_mixed_statuses_success(self):
        task_id = self.run_action("grouped")
        self.set_task_status(task_id, RUNNING)
        self.set_job_status(task_id, A_OWN, SUCCESS)
        self.set_job_status(task_id, NESTED_0, RUNNING)
        # NESTED_1 stays CREATED

        response = self.terminate(task_id, {"group": "a"})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(
            task_id,
            {
                PREPARE: CREATED,
                A_OWN: SUCCESS,
                NESTED_0: REVOKING,
                NESTED_1: REVOKED,
                AB_0: CREATED,
                FINISH: CREATED,
            },
        )
        self.assert_task_status(task_id, RUNNING)
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "Group A" cancelled',
            result="success",
            object_=self.cluster,
        )

    # -- concurrent change: a job moved out of the bulk update's `previous` status set (e.g. by the
    # runner) between the plan snapshot and the guarded update is left alone, not treated as an error --

    def test_change_status_of_jobs_skips_job_changed_since_read(self):
        task_id = self.run_action("grouped")
        self.set_job_status(task_id, AB_0, RUNNING)
        job_id = JobLog.objects.get(task_id=task_id, spec_key=AB_0).id

        changed = JobRepo().change_status_of_jobs(ids=[job_id], previous=(CREATED,), new=REVOKED)

        self.assertEqual(changed, 0)
        self.assert_jobs(task_id, ALL_CREATED | {AB_0: RUNNING})

    # -- S3/S7: unknown group name / display name used instead of internal name --

    @parametrize(
        "group_name",
        [
            param("missing", id="unknown"),
            param("Group A", id="display_name_of_a"),
            param("{x}", id="braces_in_name"),
        ],
    )
    def test_terminate_unknown_group_name_fail(self, group_name: str):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, {"group": group_name})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- names that could escape the display name lookup query: never match, nothing is touched --

    @parametrize(
        "group_name",
        [
            param("a'; DELETE FROM cm_tasklog; --", id="sql"),
            param('a" || @.names.internal like_regex ".*', id="jsonpath"),
            param("$name", id="jsonpath_variable"),
        ],
    )
    def test_terminate_group_name_injection_fail(self, group_name: str):
        task_id = self.run_action("grouped")
        tasks_before = list(TaskLog.objects.order_by("id").values_list("id", "status"))

        response = self.terminate(task_id, {"group": group_name})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assertListEqual(list(TaskLog.objects.order_by("id").values_list("id", "status")), tasks_before)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- group names/display names tricky for audit: numeric-looking name, braces and too long display name --

    @parametrize(
        "group_name,terminated_key,display_name",
        [
            param(5, FIVE_0, "Group Five", id="numeric_name"),
            param("braced", BRACED_0, "Group {braced} {0}", id="braces_in_display_name"),
        ],
    )
    def test_terminate_named_group_success(self, group_name: str | int, terminated_key: str, display_name: str):
        task_id = self.run_action("named_groups")

        response = self.terminate(task_id, {"group": group_name})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(task_id, NAMED_GROUPS_ALL_CREATED | {terminated_key: REVOKED})
        self.assert_audit(
            name=f'{self.action_display_name("named_groups")} group "{display_name}" cancelled',
            result="success",
            object_=self.cluster,
        )

    def test_terminate_group_too_long_display_name_audit_truncated(self):
        task_id = self.run_action("named_groups")

        response = self.terminate(task_id, {"group": "long"})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(task_id, NAMED_GROUPS_ALL_CREATED | {LONG_0: REVOKED})
        record = self.check_last_audit_record(
            operation_name__startswith=f'{self.action_display_name("named_groups")} group "ggg',
            operation_name__endswith='...<truncated>" cancelled',
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster),
        )
        self.assertLessEqual(len(record.operation_name), 2000)

    # -- task without execution plan: no group can be matched, so none is named.
    # The repo reports a missing plan as not found; its message tells it apart from an unknown task --

    def test_terminate_group_task_without_execution_plan_fail(self):
        task_id = self.run_action("grouped")
        TaskLog.objects.filter(id=task_id).update(execution_plan=None)

        response = self.terminate(task_id, {"group": "a"})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(response.json()["desc"], f"Task identified by {task_id} has no stored execution plan")
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- S4/S6: nothing to terminate (group finished, or already in a termination status) --

    @parametrize(
        "ab_status",
        [
            param(SUCCESS, id="finished"),
            param(REVOKED, id="already_revoked"),
            param(REVOKING, id="already_revoking"),
            param(TERMINATING, id="already_terminating"),
        ],
    )
    def test_terminate_group_nothing_to_terminate_fail(self, ab_status: ExecutionStatus):
        task_id = self.run_action("grouped")
        self.set_task_status(task_id, RUNNING)
        self.set_job_status(task_id, AB_0, ab_status)

        response = self.terminate(task_id, {"group": "ab"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.content)
        self.assert_jobs(task_id, ALL_CREATED | {AB_0: ab_status})
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "Group AB" cancelled',
            result="fail",
            object_=self.cluster,
        )

    # -- S5: nested group only, parent's own jobs and the "ab" sibling are untouched --

    def test_terminate_nested_group_only_leaves_siblings_untouched(self):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, {"group": "nested"})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(task_id, ALL_CREATED | {NESTED_0: REVOKED, NESTED_1: REVOKED})
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "Nested Of A" cancelled',
            result="success",
            object_=self.cluster,
        )

    # -- S8: task already finished --

    @parametrize(
        "task_status", [param(SUCCESS, id="success"), param(FAILED, id="failed"), param(ABORTED, id="aborted")]
    )
    def test_terminate_group_finished_task_fail(self, task_status: ExecutionStatus):
        task_id = self.run_action("grouped")
        self.set_task_status(task_id, task_status)

        response = self.terminate(task_id, {"group": "a"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "Group A" cancelled',
            result="fail",
            object_=self.cluster,
        )

    # -- unknown group on a finished task: plan/group check happens before task status is even considered --

    def test_terminate_unknown_group_finished_task_fail(self):
        task_id = self.run_action("grouped")
        self.set_task_status(task_id, SUCCESS)

        response = self.terminate(task_id, {"group": "missing"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, SUCCESS)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- A8: action forbids task termination, group termination is still allowed --

    def test_terminate_group_action_forbids_task_termination_success(self):
        task_id = self.run_action("grouped_not_terminatable")

        response = self.terminate(task_id, {"group": "a"})

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_jobs(task_id, ALL_CREATED | {A_OWN: REVOKED, NESTED_0: REVOKED, NESTED_1: REVOKED})
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f'{self.action_display_name("grouped_not_terminatable")} group "Group A" cancelled',
            result="success",
            object_=self.cluster,
        )

    # -- A3: body present, `group` absent (legacy `name` field included, there's no fallback to it) --
    # no group is named, so it's audited as task termination

    @parametrize("body", [param({"foo": 1}, id="unknown_field"), param({"name": "a"}, id="legacy_name_field")])
    def test_terminate_body_without_group_fail(self, body: dict[str, Any]):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, body)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(name=f"{self.action_display_name('grouped')} cancelled", result="fail", object_=self.cluster)

    # -- A6/A11: `group` present but invalid --

    @parametrize(
        "body",
        [
            param({"group": None}, id="group_none"),
            param({"group": ""}, id="group_blank"),
            param({"group": "  "}, id="group_whitespace"),
            param({"group": True}, id="group_bool"),
            param({"group": ["a"]}, id="group_list"),
            param({"group": "a\u0000"}, id="group_with_nul"),
        ],
    )
    def test_terminate_invalid_body_fail(self, body: dict[str, Any]):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, body)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- body variants that mean "no body": task termination, unchanged from today --

    @parametrize("body", [param(None, id="none"), param({}, id="empty_dict"), param(["a"], id="non_object_json")])
    def test_terminate_without_group_name_terminates_task(self, body: dict | list | None):
        task_id = self.run_action("grouped")

        response = self.terminate(task_id, body)

        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        self.assert_task_status(task_id, REVOKED)
        # task-level termination only flips the task's own status, jobs are left for the runner
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} cancelled", result="success", object_=self.cluster
        )

    def test_terminate_invalid_utf8_body_fail(self):
        task_id = self.run_action("grouped")

        response = self.client.post(
            path=self.terminate_node(task_id).path, data=b'{"group": "\xff"}', content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(name=f"{self.action_display_name('grouped')} cancelled", result="fail", object_=self.cluster)

    def test_terminate_lone_surrogate_in_group_fail(self):
        task_id = self.run_action("grouped")

        response = self.client.post(
            path=self.terminate_node(task_id).path, data=b'{"group": "a\\ud800"}', content_type="application/json"
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST, response.content)
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} group cancelled", result="fail", object_=self.cluster
        )

    # -- A5: forbidden --

    def test_terminate_group_denied(self):
        task_id = self.run_action("grouped")

        test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.uc.create_user(**test_user_credentials)
        self.client.login(**test_user_credentials)

        response = self.terminate(task_id, {"group": "a"})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND, response.content)
        self.assert_audit(
            name=f'{self.action_display_name("grouped")} group "Group A" cancelled',
            result="denied",
            object_=self.cluster,
            username=test_user_credentials["username"],
        )

        self.client.login(username="admin", password="admin")
        self.assert_jobs(task_id, ALL_CREATED)

    # -- forbidden user on a task without execution plan: group termination's 404 is about the missing plan,
    # task termination's one stays about access --

    @parametrize(
        "body,audit_name_suffix,audit_result",
        [
            param({"group": "a"}, "group cancelled", "fail", id="group_termination"),
            param(None, "cancelled", "denied", id="task_termination"),
        ],
    )
    def test_terminate_task_without_execution_plan_by_forbidden_user(
        self, body: dict[str, Any] | None, audit_name_suffix: str, audit_result: str
    ):
        task_id = self.run_action("grouped")
        TaskLog.objects.filter(id=task_id).update(execution_plan=None)

        test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.uc.create_user(**test_user_credentials)
        self.client.login(**test_user_credentials)

        response = self.terminate(task_id, body)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND, response.content)
        self.assert_audit(
            name=f"{self.action_display_name('grouped')} {audit_name_suffix}",
            result=audit_result,
            object_=self.cluster,
            username=test_user_credentials["username"],
        )

        self.client.login(username="admin", password="admin")
        self.assert_jobs(task_id, ALL_CREATED)
        self.assert_task_status(task_id, CREATED)

    # -- A7: unknown task --

    def test_terminate_group_unknown_task_fail(self):
        self.run_action("grouped")  # so `get_non_existent_pk` has an existing row to look past

        response = self.terminate(self.get_non_existent_pk(TaskLog), {"group": "a"})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND, response.content)
        self.assert_audit(name="Task group cancelled", result="fail", object_=None)
