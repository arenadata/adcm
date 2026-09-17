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

from itertools import chain
from pathlib import Path
from typing import Final

from cm.errors import AdcmEx
from cm.models import Action, JobLog, TaskLog
from cm.tests.scripts import retrieve_rich_jobs
from rest_framework.status import HTTP_200_OK
from unittest_parametrize import param, parametrize

from tests.suites import ADCMDjangoAPISuite

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "script_groups"

RUN_ACTION_PAYLOAD: Final = {"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}

# keys and names of jobs in the order execution plan defines,
# the same for statically declared scripts and rendered ones
EXPECTED_PLAN: Final = [
    ("/0", "prepare"),
    ("/shards/shard_a/0", "step"),
    ("/shards/shard_a/1", "step"),
    ("/shards/shard_a/2", "finish"),
    ("/shards/shard_b/0", "step"),
    ("/2", "finish"),
]


class TestScriptGroups(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.groups_bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster")
        cls.groups_cluster = cls.uc.add_cluster(bundle=cls.groups_bundle, name="With Script Groups")

    def test_scripts_stored_only_when_declared_success(self) -> None:
        stored = dict(Action.objects.filter(prototype=self.groups_cluster.prototype).values_list("name", "scripts"))

        # stored plan doesn't keep order of its scripts, hierarchy does
        self.assertCountEqual(stored["grouped"]["scripts"], [key for key, _ in EXPECTED_PLAN])
        # scripts rendered from template are unknown until rendering
        self.assertIsNone(stored["grouped_rendered"])

    @parametrize("action_name", [param("grouped", id="scripts"), param("grouped_rendered", id="scripts_template")])
    def test_run_action_with_groups_success(self, action_name: str) -> None:
        action = Action.objects.get(prototype=self.groups_cluster.prototype, name=action_name)

        response = self.client.v2[self.groups_cluster, "actions", action, "run"].post(data=RUN_ACTION_PAYLOAD)

        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        task = TaskLog.objects.get(id=response.json()["id"])

        # jobs follow execution plan
        rich_jobs = retrieve_rich_jobs(task.id)
        self.assertEqual([(job.spec.key, job.spec.names.internal) for job in rich_jobs], EXPECTED_PLAN)

        self.task_runner().launch_task(task.id)

        task.refresh_from_db()
        jobs = {job.spec_key: job for job in JobLog.objects.filter(task=task)}
        jobs_in_plan_order = [jobs[key] for key, _ in EXPECTED_PLAN]

        # task and jobs are presented as succeeded, jobs in the order of plan
        task_response = self.client.v2[task].get()
        self.assertEqual(task_response.status_code, HTTP_200_OK)
        self.assertEqual(task_response.json()["status"], "success")
        self.assertEqual(
            [(job["name"], job["status"]) for job in task_response.json()["childJobs"]],
            [(name, "success") for _, name in EXPECTED_PLAN],
        )

        job_responses = [self.client.v2[job].get() for job in jobs_in_plan_order]
        self.assertEqual(
            [(r.status_code, r.json()["status"]) for r in job_responses],
            [(HTTP_200_OK, "success")] * len(EXPECTED_PLAN),
        )

        # jobs are executed one after another: moments are compared non-strictly,
        # since jobs do nothing in here and may share the same timestamps
        moments = [
            task.start_date,
            *chain.from_iterable((job.start_date, job.finish_date) for job in jobs_in_plan_order),
            task.finish_date,
        ]
        self.assertEqual(moments, sorted(moments))

    @parametrize(
        "bundle_name,expected_content",
        [
            param(
                "reused_group_name",
                ("Jobs are defined incorrectly", "twin", "is used by more than one group"),
                id="reused_group_name",
            ),
            param(
                "group_named_after_script_position",
                ("Jobs are defined incorrectly", '"/0" is declared more than once', "as script, then as group"),
                id="group_named_after_script_position",
            ),
        ],
    )
    def test_upload_incorrect_groups_fail(self, bundle_name: str, expected_content: tuple[str, ...]) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.uc.upload_bundle(BUNDLES_DIR / bundle_name)

        self.assertEqual(err.exception.code, "BUNDLE_DEFINITION_ERROR")
        for content in expected_content:
            self.assertIn(content, err.exception.msg)
