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
Upgrade of 3.0.0 data by `cm.0156_execution_plan_storage`.

3.0.0 rows come from `files/execution_plan_migration_3_0_0.yaml`,
what 0156 has to store for them is in `files/execution_plan_migration_expected.yaml`.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.action import wizard
from django.apps.registry import Apps
from django_test_migrations.contrib.unittest_case import MigratorTestCase
import yaml

from cm.impl.common.execution_plan import parse_execution_plan
from cm.impl.wizard.repo import to_step_operation_spec

FILES_DIR = Path(__file__).parent / "files"
FIXTURE_PATH = FILES_DIR / "execution_plan_migration_3_0_0.yaml"
EXPECTED_PATH = FILES_DIR / "execution_plan_migration_expected.yaml"


@dataclass(slots=True)
class SeededIDs:
    """Ids of seeded rows by case name"""

    actions: dict[str, int] = field(default_factory=dict)
    tasks: dict[str, int] = field(default_factory=dict)
    orphan_jobs: dict[str, int] = field(default_factory=dict)
    steps: dict[str, int] = field(default_factory=dict)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def seed_3_0_0_rows(apps: Apps, fixture: dict[str, Any]) -> SeededIDs:
    """Create rows of the fixture through models of the migration state, in the order they are listed"""

    ids = SeededIDs()

    bundle = apps.get_model("cm", "Bundle").objects.create(**fixture["bundle"])
    prototype = apps.get_model("cm", "Prototype").objects.create(bundle=bundle, **fixture["prototype"])

    seed_actions(apps=apps, prototype=prototype, actions=fixture["actions"], ids=ids)
    seed_tasks(apps=apps, tasks=fixture["tasks"], ids=ids)
    seed_orphan_jobs(apps=apps, jobs=fixture["orphan_jobs"], ids=ids)
    seed_processes(apps=apps, processes=fixture["processes"], ids=ids)

    return ids


def seed_actions(apps: Apps, prototype: Any, actions: dict[str, Any], ids: SeededIDs) -> None:
    action_model = apps.get_model("cm", "Action")
    subaction_model = apps.get_model("cm", "SubAction")

    for case, definition in actions.items():
        fields = {key: value for key, value in definition.items() if key != "subactions"}
        action = action_model.objects.create(name=case, prototype=prototype, **fields)
        ids.actions[case] = action.id

        for subaction in definition["subactions"]:
            subaction_model.objects.create(action=action, **subaction)


def seed_tasks(apps: Apps, tasks: dict[str, Any], ids: SeededIDs) -> None:
    content_type_model = apps.get_model("contenttypes", "ContentType")
    task_model = apps.get_model("cm", "TaskLog")
    job_model = apps.get_model("cm", "JobLog")

    for case, definition in tasks.items():
        object_type, _ = content_type_model.objects.get_or_create(app_label="cm", model=definition["object_type"])
        task = task_model.objects.create(
            action_id=ids.actions[definition["action"]],
            object_type=object_type,
            object_id=definition["object_id"],
            status=definition["status"],
        )
        ids.tasks[case] = task.id

        for job in definition["jobs"]:
            job_model.objects.create(task=task, **job)


def seed_orphan_jobs(apps: Apps, jobs: dict[str, Any], ids: SeededIDs) -> None:
    job_model = apps.get_model("cm", "JobLog")

    for case, job in jobs.items():
        ids.orphan_jobs[case] = job_model.objects.create(task=None, **job).id


def seed_processes(apps: Apps, processes: dict[str, Any], ids: SeededIDs) -> None:
    process_model = apps.get_model("cm", "Process")
    step_model = apps.get_model("cm", "ProcessStep")

    for definition in processes.values():
        process = process_model.objects.create(
            action_id=ids.actions[definition["action"]],
            state=definition["state"],
            # flow isn't read by the migration, only a valid row is needed
            flow_spec=[],
            sync_key=uuid4(),
        )

        for case, step in definition["steps"].items():
            ids.steps[case] = step_model.objects.create(process=process, **step).id


def node_identity(node: dict[str, Any]) -> dict[str, Any]:
    """Part of a plan node that a job duplicates in its own columns"""

    return {
        "names": node["names"],
        "script": {"type": node["script"]["type"], "path": node["script"]["path"]},
        "on_fail": node["on_fail"],
    }


def job_identity(job: Any) -> dict[str, Any]:
    """What the job's own columns say about its node, after the normalizations of the conversion"""

    return {
        "names": {"internal": job.name, "display": job.display_name},
        "script": {"type": job.script_type, "path": job.script},
        "on_fail": {
            "state": job.state_on_fail or None,
            "multi_state_set": job.multi_state_on_fail_set,
            "multi_state_unset": job.multi_state_on_fail_unset,
        },
    }


def to_step_model(step: Any) -> wizard.ActionProcessStepModel:
    return wizard.ActionProcessStepModel(
        id=step.id,
        process_id=step.process_id,
        name=step.name,
        stage=step.stage,
        display_name=step.display_name,
        step_spec=step.step_spec,
        description=step.description,
        required=step.required,
        type=step.type,
        state=step.state,
    )


class TestExecutionPlanMigrationFrom300(MigratorTestCase):
    migrate_from = ("cm", "0155_remove_redundant_fields_from_action")
    migrate_to = ("cm", "0156_execution_plan_storage")

    ids: SeededIDs
    expected: dict[str, Any]

    def prepare(self) -> None:
        self.ids = seed_3_0_0_rows(apps=self.old_state.apps, fixture=load_yaml(FIXTURE_PATH))
        self.expected = load_yaml(EXPECTED_PATH)

    def test_subactions_become_action_scripts(self) -> None:
        expected = self.expected["actions"]
        scripts = dict(
            self.new_state.apps.get_model("cm", "Action")
            .objects.filter(id__in=self.ids.actions.values())
            .values_list("id", "scripts")
        )

        for case, plan in expected["converted"].items():
            with self.subTest(case):
                stored = scripts[self.ids.actions[case]]
                self.assertDictEqual(stored, plan)
                parse_execution_plan(stored)

        for case in expected["stay_null"]:
            with self.subTest(case):
                self.assertIsNone(scripts[self.ids.actions[case]])

    def test_jobs_become_task_plan_and_spec_keys(self) -> None:
        """
        Besides the exact stored values, `spec_key` of each job leads to the node
        that duplicates the job's own columns
        """

        expected = self.expected["tasks"]
        job_model = self.new_state.apps.get_model("cm", "JobLog")
        plans = dict(
            self.new_state.apps.get_model("cm", "TaskLog")
            .objects.filter(id__in=self.ids.tasks.values())
            .values_list("id", "execution_plan")
        )
        jobs = defaultdict(list)
        for job in job_model.objects.filter(task_id__in=self.ids.tasks.values()).order_by("id"):
            jobs[job.task_id].append(job)
        orphan_spec_keys = dict(
            job_model.objects.filter(id__in=self.ids.orphan_jobs.values()).values_list("id", "spec_key")
        )

        for case, task in expected["converted"].items():
            task_id = self.ids.tasks[case]
            plan = plans[task_id]

            with self.subTest(case):
                self.assertDictEqual(plan, task["execution_plan"])
                parse_execution_plan(plan)
                self.assertEqual([job.spec_key for job in jobs[task_id]], task["spec_keys"])
                for job in jobs[task_id]:
                    self.assertDictEqual(node_identity(plan["scripts"][job.spec_key]), job_identity(job))

        for case in expected["empty_plan"]:
            with self.subTest(case):
                self.assertDictEqual(plans[self.ids.tasks[case]], self.expected["empty_plan"])

        for case in self.expected["jobs_without_task"]:
            with self.subTest(case):
                self.assertEqual(orphan_spec_keys[self.ids.orphan_jobs[case]], "")

    def test_operation_step_specs_become_plans(self) -> None:
        expected = self.expected["steps"]
        steps = self.new_state.apps.get_model("cm", "ProcessStep").objects.in_bulk(self.ids.steps.values())

        for case, plan in expected["converted"].items():
            with self.subTest(case):
                step = steps[self.ids.steps[case]]
                self.assertDictEqual(step.step_spec, plan)
                to_step_operation_spec(step.step_spec)
                _ = to_step_model(step).spec

        for case in expected["stay_null"]:
            with self.subTest(case):
                self.assertIsNone(steps[self.ids.steps[case]].step_spec)

        for case, step_spec in expected["unchanged"].items():
            with self.subTest(case):
                self.assertEqual(steps[self.ids.steps[case]].step_spec, step_spec)
