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

"""Test audit of background operations"""

import time
from datetime import datetime, timedelta
from itertools import chain
from operator import attrgetter, itemgetter, methodcaller
from typing import Tuple

import allure
import pytest
from adcm_client.objects import Cluster, Task
from adcm_pytest_plugin.steps.commands import clearaudit, logrotate
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.functional.audit.checks import check_audit_cef_logs
from tests.functional.audit.conftest import BUNDLES_DIR, parametrize_audit_scenario_parsing, set_operations_date
from tests.library.db import set_configs_date, set_jobs_date, set_tasks_date

# pylint: disable=redefined-outer-name

RUN_SYNC_NAME = "run_ldap_sync"


@pytest.fixture()
def cluster_with_history(sdk_client_fs) -> Tuple[Cluster, Tuple[dict, ...], Tuple[Task, ...]]:
    """Create cluster, change its configs and run some actions"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "adb")
    cluster = bundle.cluster_create("Cluster with Actions")
    _ = [cluster.config_set({"just_string": str(i)}) for i in range(10)]
    configs = cluster.config_history(full=True)
    tasks = []
    for _ in range(4):
        tasks.append(cluster.action(name="install").run())
        tasks[-1].wait()
    return cluster, configs, tuple(tasks)


@pytest.fixture()
def make_objects_old(adcm_db, sdk_client_fs, cluster_with_history) -> None:
    """Change object's dates (configs, tasks and audit records)"""
    old_date = datetime.utcnow() - timedelta(days=300)
    _, configs, tasks = cluster_with_history
    old_tasks = tasks[: len(tasks) // 2]
    get_id = attrgetter("id")
    set_configs_date(adcm_db, old_date, tuple(map(itemgetter("id"), configs[: len(configs) // 2])))
    set_tasks_date(adcm_db, old_date, tuple(map(get_id, old_tasks)))
    set_jobs_date(adcm_db, old_date, tuple(map(get_id, chain.from_iterable(map(methodcaller("job_list"), old_tasks)))))
    set_operations_date(adcm_db, old_date, sdk_client_fs.audit_operation_list(paging={"limit": 4}))


@parametrize_audit_scenario_parsing("background_tasks.yaml")
@pytest.mark.usefixtures("make_objects_old", "prepare_settings")
def test_background_operations_audit(audit_log_checker, adcm_fs, sdk_client_fs):
    """Test audit of background operations"""

    def _sync_ran_finished():
        assert any(
            map(
                lambda task: (
                    task.status == "failed" and task.action_id is not None and task.action().name == RUN_SYNC_NAME
                ),
                map(methodcaller("task"), sdk_client_fs.job_list()),
            )
        )

    logrotate(adcm_fs, "all")
    clearaudit(adcm_fs)
    with allure.step("Wait until ldap sync is launched on schedule and increase ldap sync interval"):
        wait_until_step_succeeds(_sync_ran_finished, timeout=65, period=5)
        sdk_client_fs.adcm().config_set_diff(
            {
                "ldap_integration": {
                    "sync_interval": 60,
                },
            }
        )
    operations = sdk_client_fs.audit_operation_list()
    audit_log_checker.check(operations)
    with allure.step("Check that after 1 minute there is no new audit records (crobtab-related bug)"):
        # to check if there's "crontab" spawned record that shouldn't be there
        time.sleep(61)
        operations_after = len(sdk_client_fs.audit_operation_list())
        assert len(operations) == operations_after, "There should not be any new audit records"
    check_audit_cef_logs(sdk_client_fs, adcm_fs.container)
