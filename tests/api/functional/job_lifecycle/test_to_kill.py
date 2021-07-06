"""Kill created and running jobs"""
# pylint: disable=unused-argument
import allure
import pytest
from adss_client.objects import JobQueue
from pytest_lazyfixture import lazy_fixture

from tests.functional.utils.common import wait_end_job_queue, wait_job_queue_state
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.tools import random_string


@pytest.fixture()
def created_job_queue(cluster_with_jobqueue) -> JobQueue:
    """
    Job queue in state `created`
    """
    _, job_queue = cluster_with_jobqueue
    assert job_queue.state == "created", "To start test, need a Job Queue in state 'created'"
    return job_queue


@pytest.fixture()
def running_job_queue(adss_client_fs, dummy_cluster_with_mountpoint) -> JobQueue:
    """
    Job queue in state `running`
    """
    cluster = dummy_cluster_with_mountpoint
    cluster.reread()
    filesystem = cluster.mount_point_set()[0].filesystem()
    handler = adss_client_fs.handler(name="dummy_backup_handler")
    job_queue = cluster.job_queue_create(
        name=f"jobqueue-{random_string()}",
        filesystem=filesystem,
        handler=handler,
        config={"duration": 60},
    )
    wait_job_queue_state(job_queue, state="running")
    return job_queue


@pytest.mark.parametrize(
    "job_queue", [lazy_fixture("created_job_queue"), lazy_fixture("running_job_queue")]
)
@pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True)
def test_to_kill_job(adss_client_fs, job_queue, image):
    """
    Test that killed job moved to job history
    """
    with allure.step("Kill created Job Queue"):
        job_queue.state = 'to kill'
        job_queue.save()

    with allure.step("Assert that Job Queue was killed"):
        wait_end_job_queue(adss_client=adss_client_fs, job_queue=job_queue, timeout=30)
        job_history = adss_client_fs.job_history(id=job_queue.id)
        assert job_history.state == 'killed'
