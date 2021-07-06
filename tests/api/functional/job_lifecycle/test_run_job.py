"""Create and run jobs"""
# pylint: disable=redefined-outer-name
import time
from typing import Tuple

import allure
import pytest
from adss_client.objects import (
    Cluster,
    CronLine,
)

from tests.functional.utils.common import (
    wait_appear_job_queue,
    wait_end_job_queue,
    wait_job_queue_state,
)
from tests.functional.utils.fixtures import CRON_LINE_TEST_VALUE
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.tools import random_string

pytestmark = pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True)

DEFAULT_DURATION = 29
DEFAULT_ZERO_CAPACITY = 0


@pytest.fixture(
    params=[CRON_LINE_TEST_VALUE, DEFAULT_ZERO_CAPACITY, DEFAULT_DURATION],
    ids=["every_hour_cronline"],
)
def cluster_with_custom_cronline(
    request, adss_client_fs, dummy_cluster_with_mountpoint
) -> Tuple[Cluster, CronLine]:
    """Prepare Cluster with custom Cron Line."""
    cron, capacity_value, duration = request.param
    cluster = dummy_cluster_with_mountpoint
    cluster.reread()
    with allure.step(f"Set all capacity for {cluster.name} to {capacity_value}"):
        for capacity in cluster.cluster_capacity_set():
            capacity.value = capacity_value
            capacity.save()
    with allure.step(f"Create cron line for '{cluster.name}'"):
        cron_line = cluster.cron_line_create(
            name=f"cronline-{random_string()}",
            filesystem=cluster.mount_point_set()[0].filesystem(),
            handler=adss_client_fs.handler(name="dummy_backup_handler"),
            config={"duration": duration},
            cron_line=cron,
        )
    return cluster, cron_line


@pytest.mark.parametrize(
    "cluster_with_custom_cronline",
    [("* * * * * ", 2, DEFAULT_DURATION)],
    ids=["every_minute_cronline"],
    indirect=True,
)
def test_run_job_by_cron(adss_client_fs, cluster_with_custom_cronline):
    """Tests running job by cronline."""
    _, cronline = cluster_with_custom_cronline
    wait_appear_job_queue(adss_client_fs, cron_name=cronline.name, timeout=70)


@pytest.mark.parametrize(
    "cluster_with_custom_cronline",
    [("* * * * * *", 2, 15)],
    ids=["every_second_cronline"],
    indirect=True,
)
def test_no_job_duplication_by_cron(adss_client_fs, cluster_with_custom_cronline):
    """Tests that job is not starting until one is running."""
    _, cronline = cluster_with_custom_cronline
    first_job_queue = wait_appear_job_queue(adss_client_fs, cron_name=cronline.name, timeout=70)
    wait_job_queue_state(first_job_queue, state="running")
    with allure.step("Check no second job while the first is running"):
        start = time.time()
        while time.time() - start < 10:
            time.sleep(2)
            assert (
                len(list(adss_client_fs.job_queue_iter())) == 1
            ), "There are more than one job in queue"
    wait_end_job_queue(adss_client_fs, first_job_queue)
    with allure.step("Check the second job started after first one is end"):
        second_job_queue = wait_appear_job_queue(
            adss_client_fs, cron_name=cronline.name, timeout=70
        )
        wait_job_queue_state(second_job_queue, state="running")
        assert (
            len(list(adss_client_fs.job_history_iter())) == 1
        ), "There are more than one job in history"
        assert (
            len(list(adss_client_fs.job_queue_iter())) == 1
        ), "There are more than one job in queue"
