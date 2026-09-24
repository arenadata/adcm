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
Execution flow of celery canvas built by `prepare_execution_plan`, run by a real worker.

Structure of canvas is covered by `test_execution_plan`,
these tests check how celery actually runs it:
which jobs are started after failures, and that task finalization happens exactly once.

Setup:
- worker is started in threads of the test process (`celery.contrib.testing.worker.start_worker`)
  with ADCM PostgreSQL transport and database result backend, both pointed at the test database;
- ADCM tasks are replaced by stubs registered under the same names,
  they only record calls, so no ADCM logic (statuses, concerns, etc.) is involved;
- every plan is started through a stub doing `self.replace(...)`, as it's done in production.

Caveats:
- tests are tagged with `CELERY_WORKER_TAG`, so they can be excluded from run (`--exclude-tag`);
- tests are slow: chord failure is detected by `chord_unlock` polling (~1s),
  and every test waits a bit after finalization to catch late or duplicated calls;
- ordering within parallel groups isn't deterministic,
  so only content of flow and relative order of its meaningful points are checked;
- "slow" jobs rely on `sleep` to finish after failed ones, so heavily loaded machine may affect them;
- stubs must be registered on the app before it's finalized:
  importing `integrations.celery.tasks` registers real shared tasks under the same names,
  and they take precedence otherwise;
- SQLAlchemy engines of transport and result backend bypass Django,
  so they're disposed explicitly, otherwise test database can't be dropped;
- kombu and result tables aren't cleaned between tests, every plan uses its own task id instead;
- celery app is configured from `CelerySettings` built like in production,
  but it's plain `Celery` rather than `ADCMCelery`, since stubs don't need DI container;
- all of this is checked with celery 5.6.3, only database result backend is covered.
"""

from collections.abc import Callable, Collection
from itertools import count
from typing import ClassVar, NamedTuple
import time
import threading

from core.action import ExecutionStatus
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStyle,
    GroupSpec,
    JobShortInfo,
    JobSpecV1,
    RichJob,
    ScriptSpec,
    ScriptType,
    WorkerInfo,
)
from core.spec.keys import level_key_from_full_key
from core.spec.types import FullSpecKey
from core.types import Names
from django.conf import settings as django_settings
from django.db import connection as django_connection
from django.test import SimpleTestCase, tag
from integrations.celery.pg import transport
from integrations.celery.pg.transport import make_broker_url
from integrations.celery.settings import CelerySettings
from integrations.celery.tasks import (
    COMPLETE_TASK_TASK_NAME,
    GROUP_FINISHED_TASK_NAME,
    RUN_JOB_TASK_NAME,
    SET_TASK_TO_BROKEN_TASK_NAME,
    prepare_execution_plan,
)
from sqlalchemy import URL

from celery import Celery, Task
from celery.contrib.testing.worker import start_worker

CELERY_WORKER_TAG = "celery_worker"

START_PLAN_TASK_NAME = "adcm:tests:start-plan"

SEQUENTIAL = ExecutionStyle.SEQUENTIAL
PARALLEL = ExecutionStyle.PARALLEL

FINALIZATION_TIMEOUT = 30
# long enough for `chord_unlock` retry to happen, so duplicated or late calls are caught
SETTLE_DELAY = 2
SLOW_JOB_DURATION = 1

FINALIZE = ("finalize",)
BROKEN = ("broken",)


def start(key: str) -> tuple[str, str]:
    return "start", key


def end(key: str) -> tuple[str, str]:
    return "end", key


def fail(key: str) -> tuple[str, str]:
    return "fail", key


def skip(key: str) -> tuple[str, str]:
    return "skip", key


def group_finished(key: str) -> tuple[str, str]:
    return "group-finished", key


def make_script(key: str) -> ScriptSpec:
    name = level_key_from_full_key(FullSpecKey(key))

    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=name),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
    )


def make_group(key: str, type_: ExecutionStyle) -> GroupSpec:
    name = level_key_from_full_key(FullSpecKey(key))

    return GroupSpec(key=FullSpecKey(key), names=Names(internal=name, display=name), type=type_)


def make_jobs(task_id: int, plan: JobSpecV1) -> dict[FullSpecKey, RichJob]:
    return {
        key: RichJob(
            spec=script,
            runtime=JobShortInfo(
                id=task_id * 100 + i,
                task_id=task_id,
                spec_key=key,
                finish_date=None,
                worker=WorkerInfo(),
                status=ExecutionStatus.CREATED,
            ),
        )
        for i, (key, script) in enumerate(plan.scripts.items())
    }


class StubTask(NamedTuple):
    name: str
    func: Callable
    bind: bool


class FlowRecorder:
    """Plans to run and what happened during their execution, shared between test and worker threads"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.task_ids = count(start=1)
        self.plans: dict[int, JobSpecV1] = {}
        self.jobs: dict[int, dict[FullSpecKey, RichJob]] = {}
        self.failing: dict[int, Collection[str]] = {}
        self.revoked: dict[int, Collection[str]] = {}
        self.slow: dict[int, Collection[str]] = {}
        self.failing_finalization: set[int] = set()
        self.events: dict[int, list[tuple[str, ...]]] = {}

    def add_plan(
        self,
        plan: JobSpecV1,
        failing: Collection[str],
        revoked: Collection[str],
        slow: Collection[str],
        fail_finalization: bool,
    ) -> int:
        with self.lock:
            task_id = next(self.task_ids)
            self.plans[task_id] = plan
            self.jobs[task_id] = make_jobs(task_id=task_id, plan=plan)
            self.failing[task_id] = failing
            self.revoked[task_id] = revoked
            self.slow[task_id] = slow
            if fail_finalization:
                self.failing_finalization.add(task_id)

        return task_id

    def record(self, task_id: int, event: tuple[str, ...]) -> None:
        with self.lock:
            self.events.setdefault(task_id, []).append(event)

    def events_of(self, task_id: int) -> list[tuple[str, ...]]:
        with self.lock:
            return list(self.events.get(task_id, ()))

    def key_of(self, task_id: int, job_id: int) -> str:
        return next(str(key) for key, job in self.jobs[task_id].items() if job.runtime.id == job_id)


def build_celery_settings() -> CelerySettings:
    """
    Build settings the same way `EnvironmentProvider.celery_settings` does.
    Connection is taken from Django rather than from environment,
    because test database (and its clones in parallel run) is named differently.
    """

    database = django_connection.settings_dict
    connection_str = URL.create(
        "postgresql+psycopg",
        username=database["USER"],
        password=database["PASSWORD"],
        host=database["HOST"],
        port=int(database["PORT"]),
        database=database["NAME"],
        query={key: str(value) for key, value in database["OPTIONS"].items()},
    ).render_as_string(hide_password=False)

    return CelerySettings(
        db_url=connection_str,
        broker_url=make_broker_url(connection_str),
        result_backend=f"db+{connection_str}",
        consul=None,
        default_adcm_url=None,
        status_service_base_path=django_settings.STATUS_SERVICE_BASE_PATH,
    )


def build_celery_app(settings: CelerySettings) -> Celery:
    # configured the same way as `ADCMCelery`, which isn't used only because stubs don't need DI container
    app = Celery("adcm-flow-tests")
    app.config_from_object(settings)
    return app


def build_stub_tasks(recorder: FlowRecorder) -> tuple[StubTask, ...]:
    def start_plan(self: Task, task_id: int) -> None:
        plan = prepare_execution_plan(task_id=task_id, plan=recorder.plans[task_id], jobs=recorder.jobs[task_id])
        return self.replace(plan)

    def run_job(*_, task_id: int, job_id: int, **__) -> None:
        key = recorder.key_of(task_id=task_id, job_id=job_id)

        if key in recorder.revoked[task_id]:
            recorder.record(task_id, skip(key))
            return

        recorder.record(task_id, start(key))

        if key in recorder.slow[task_id]:
            time.sleep(SLOW_JOB_DURATION)

        if key in recorder.failing[task_id]:
            recorder.record(task_id, fail(key))
            message = f"Job {key} failed"
            raise RuntimeError(message)

        recorder.record(task_id, end(key))

    def group_finished_callback(*_, task_id: int, group_key: str, **__) -> None:
        recorder.record(task_id, group_finished(group_key))

    def complete_task(*_, task_id: int, **__) -> None:
        recorder.record(task_id, FINALIZE)

        if task_id in recorder.failing_finalization:
            message = f"Finalization of task {task_id} failed"
            raise RuntimeError(message)

    def set_task_to_broken(*_, task_id: int, **__) -> None:
        recorder.record(task_id, BROKEN)

    return (
        StubTask(name=START_PLAN_TASK_NAME, func=start_plan, bind=True),
        StubTask(name=RUN_JOB_TASK_NAME, func=run_job, bind=False),
        StubTask(name=GROUP_FINISHED_TASK_NAME, func=group_finished_callback, bind=False),
        StubTask(name=COMPLETE_TASK_TASK_NAME, func=complete_task, bind=False),
        StubTask(name=SET_TASK_TO_BROKEN_TASK_NAME, func=set_task_to_broken, bind=False),
    )


def register_stub_tasks(app: Celery, stubs: Collection[StubTask]) -> None:
    # registered eagerly, before app is finalized, to take precedence over real shared tasks
    for stub in stubs:
        app.task(name=stub.name, bind=stub.bind, lazy=False, shared=False)(stub.func)

    # required by ping check of started worker
    import celery.contrib.testing.tasks  # noqa: F401

    app.finalize()

    for stub in stubs:
        run = app.tasks[stub.name].run
        # bound task's `run` is a method wrapping the function
        if getattr(run, "__func__", run) is not stub.func:
            message = f"Task {stub.name} isn't replaced with stub, got {run}"
            raise RuntimeError(message)


@tag(CELERY_WORKER_TAG)
class TestExecutionFlow(SimpleTestCase):
    # database is required only for broker and result backend, which work through SQLAlchemy,
    # so Django's per-test transactions are of no use in here
    databases = {"default"}

    app: ClassVar[Celery]
    recorder: ClassVar[FlowRecorder]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.recorder = FlowRecorder()
        cls.app = build_celery_app(build_celery_settings())
        cls.app.set_current()
        register_stub_tasks(app=cls.app, stubs=build_stub_tasks(cls.recorder))

        cls.addClassCleanup(cls.release_connections)

        worker = start_worker(cls.app, pool="threads", concurrency=4, shutdown_timeout=30)
        worker.__enter__()
        cls.addClassCleanup(worker.__exit__, None, None, None)

    @classmethod
    def release_connections(cls) -> None:
        cls.app.pool.force_close_all()
        cls.app.backend.session_manager.invalidate(cls.app.backend.url)
        cls.app.close()

        # the engine cache must not outlive the test database
        for engine, _ in transport._ENGINES.values():
            engine.dispose()
        transport._ENGINES.clear()

    def run_plan(
        self,
        *entries: ScriptSpec | GroupSpec,
        failing: Collection[str] = (),
        revoked: Collection[str] = (),
        slow: Collection[str] = (),
        fail_finalization: bool = False,
    ) -> list[tuple[str, ...]]:
        """Run plan of given entries till task is finalized and return what happened in order it happened"""

        task_id = self.recorder.add_plan(
            plan=JobSpecV1.from_entries(*entries),
            failing=failing,
            revoked=revoked,
            slow=slow,
            fail_finalization=fail_finalization,
        )

        self.app.tasks[START_PLAN_TASK_NAME].apply_async(kwargs={"task_id": task_id})

        deadline = time.monotonic() + FINALIZATION_TIMEOUT
        while FINALIZE not in self.recorder.events_of(task_id):
            if time.monotonic() > deadline:
                events = self.recorder.events_of(task_id)
                self.fail(f"Task isn't finalized in {FINALIZATION_TIMEOUT}s, events: {events}")
            time.sleep(0.1)

        time.sleep(SETTLE_DELAY)

        return self.recorder.events_of(task_id)

    def test_successful_plan_runs_all_jobs_and_finalizes_task_once(self) -> None:
        events = self.run_plan(
            make_script("/0"),
            make_group("/p", PARALLEL),
            make_group("/p/s", SEQUENTIAL),
            make_script("/p/s/0"),
            make_script("/p/s/1"),
            make_script("/p/0"),
            make_script("/1"),
        )

        self.assertCountEqual(
            events,
            [
                start("/0"),
                end("/0"),
                start("/p/s/0"),
                end("/p/s/0"),
                start("/p/s/1"),
                end("/p/s/1"),
                start("/p/0"),
                end("/p/0"),
                group_finished("/p"),
                start("/1"),
                end("/1"),
                FINALIZE,
            ],
        )
        self.assertLess(events.index(end("/0")), events.index(start("/p/s/0")))
        self.assertLess(events.index(end("/0")), events.index(start("/p/0")))
        self.assertLess(events.index(end("/p/s/0")), events.index(start("/p/s/1")))
        self.assertLess(events.index(end("/p/s/1")), events.index(group_finished("/p")))
        self.assertLess(events.index(end("/p/0")), events.index(group_finished("/p")))
        self.assertLess(events.index(group_finished("/p")), events.index(start("/1")))
        self.assertEqual(events[-1], FINALIZE)

    def test_failed_sequential_job_stops_plan(self) -> None:
        events = self.run_plan(make_script("/0"), make_script("/1"), failing={"/0"})

        self.assertEqual(events, [start("/0"), fail("/0"), FINALIZE])

    def test_revoked_sequential_job_is_skipped_and_plan_continues(self) -> None:
        events = self.run_plan(make_script("/0"), make_script("/1"), make_script("/2"), revoked={"/1"})

        self.assertEqual(events, [start("/0"), end("/0"), skip("/1"), start("/2"), end("/2"), FINALIZE])

    def test_revoked_branch_job_is_skipped_and_plan_continues(self) -> None:
        events = self.run_plan(
            make_group("/p", PARALLEL),
            make_script("/p/0"),
            make_script("/p/1"),
            make_script("/0"),
            revoked={"/p/0"},
        )

        self.assertCountEqual(
            events, [skip("/p/0"), start("/p/1"), end("/p/1"), group_finished("/p"), start("/0"), end("/0"), FINALIZE]
        )
        self.assertEqual(events[-4:], [group_finished("/p"), start("/0"), end("/0"), FINALIZE])

    def test_failed_branch_stops_only_itself_and_task_is_finalized_after_other_branches(self) -> None:
        events = self.run_plan(
            make_script("/0"),
            make_group("/p", PARALLEL),
            make_group("/p/s", SEQUENTIAL),
            make_script("/p/s/0"),
            make_script("/p/s/1"),
            make_script("/p/0"),
            make_script("/1"),
            failing={"/p/s/0"},
            slow={"/p/0"},
        )

        self.assertCountEqual(
            events,
            [
                start("/0"),
                end("/0"),
                start("/p/s/0"),
                fail("/p/s/0"),
                start("/p/0"),
                end("/p/0"),
                FINALIZE,
            ],
        )
        self.assertLess(events.index(end("/p/0")), events.index(FINALIZE))

    def test_failed_branch_of_last_group_finalizes_task_after_other_branches(self) -> None:
        events = self.run_plan(
            make_script("/0"),
            make_group("/p", PARALLEL),
            make_script("/p/0"),
            make_script("/p/1"),
            failing={"/p/0"},
            slow={"/p/1"},
        )

        self.assertCountEqual(
            events,
            [start("/0"), end("/0"), start("/p/0"), fail("/p/0"), start("/p/1"), end("/p/1"), FINALIZE],
        )
        self.assertLess(events.index(end("/p/1")), events.index(FINALIZE))

    def test_failed_job_after_parallel_group_stops_plan(self) -> None:
        # job right after parallel group is moved by celery into chord's body
        events = self.run_plan(
            make_group("/p", PARALLEL),
            make_script("/p/0"),
            make_script("/p/1"),
            make_script("/0"),
            make_script("/1"),
            failing={"/0"},
        )

        self.assertCountEqual(
            events,
            [
                start("/p/0"),
                end("/p/0"),
                start("/p/1"),
                end("/p/1"),
                group_finished("/p"),
                start("/0"),
                fail("/0"),
                FINALIZE,
            ],
        )
        self.assertEqual(events[-4:], [group_finished("/p"), start("/0"), fail("/0"), FINALIZE])

    def test_failed_parallel_group_stops_following_parallel_group(self) -> None:
        events = self.run_plan(
            make_group("/a", PARALLEL),
            make_script("/a/0"),
            make_script("/a/1"),
            make_group("/b", PARALLEL),
            make_script("/b/0"),
            make_script("/b/1"),
            failing={"/a/0"},
            slow={"/a/1"},
        )

        self.assertCountEqual(events, [start("/a/0"), fail("/a/0"), start("/a/1"), end("/a/1"), FINALIZE])
        self.assertLess(events.index(end("/a/1")), events.index(FINALIZE))

    def test_failed_finalization_marks_task_broken_without_finalizing_again(self) -> None:
        events = self.run_plan(make_script("/0"), fail_finalization=True)

        self.assertEqual(events, [start("/0"), end("/0"), FINALIZE, BROKEN])
