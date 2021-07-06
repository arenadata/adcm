"""
ADSS objects creation tests
"""
# pylint: disable=unused-argument
import allure
import pytest
from coreapi.exceptions import ErrorMessage

from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.fake_data import generate_json_from_schema
from tests.utils.tools import random_string
from tests.functional.utils.common import (
    wait_end_job_queue,
    get_unsupported_handlers,
    create_job_queue,
)

pytest_plugins = ["tests.functional.utils.fixtures"]
pytestmark = [
    allure.suite("Create objects tests"),
]


@pytest.mark.positive()
def test_adb_cluster_create(adss_client_fs, cluster):
    """
    Assert that ADB cluster type exists and user can create cluster of ADB type
    """
    assert adss_client_fs.cluster(id=cluster.id), "Cluster not created"


def test_jobqueue_create_positive(adss_client_fs, cluster_with_mountpoint):
    """
    Assert that created Job Queue was taken to work and appeared in Job History
    """
    cluster_with_mountpoint.reread()
    filesystem = cluster_with_mountpoint.mount_point_set()[0].filesystem()

    job_queue = create_job_queue(adss_client_fs, cluster_with_mountpoint, filesystem)

    with allure.step(f"Assert that {job_queue} was taken to work"):
        wait_end_job_queue(adss_client_fs, job_queue)
        assert adss_client_fs.job_history(id=job_queue.id), (
            "Job Queue was not taken to work " "and did not appear in Job History"
        )


def test_jobqueue_create_without_mountpoint_negative(image, adss_client_fs, cluster, filesystem):
    """
    Assert that Job Queue create action failed because
    File System and Cluster has no connection over Mount Point
    """

    handler = next(iter(adss_client_fs.handler_iter()))
    with allure.step(f"Create Job Queue for {cluster} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            cluster.job_queue_create(
                name=f"jobqueue-{random_string()}",
                filesystem=filesystem,
                handler=handler,
                config=generate_json_from_schema(json_schema=handler.config_schema),
            )
        assert err.value.error._data["details"] == {  # pylint: disable = protected-access
            "non_field_errors": [
                f"Cluster({cluster.id}, {cluster.display_name}) "
                "has no MountPoint for "
                f"Filesystem({filesystem.id}, {filesystem.display_name})."
            ]
        }


@pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True)
def test_jobqueue_create_with_unsupported_handler_negative(
    image, adss_client_fs, cluster_with_mountpoint
):
    """
    Assert that Job Queue create action failed because
    File System and Cluster is not compatible with Handler
    """
    cluster_with_mountpoint.reread()
    filesystem = cluster_with_mountpoint.mount_point_set()[0].filesystem()

    unsupported_handler = get_unsupported_handlers(adss_client_fs, cluster_with_mountpoint)[0]

    with allure.step(f"Create Job Queue for {cluster_with_mountpoint} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            cluster_with_mountpoint.job_queue_create(
                name=f"jobqueue-{random_string()}",
                filesystem=filesystem,
                handler=unsupported_handler,
                config=generate_json_from_schema(json_schema=unsupported_handler.config_schema),
            )
        assert err.value.error._data["details"] == {  # pylint: disable = protected-access
            "non_field_errors": [
                f"Handler({unsupported_handler.id}, {unsupported_handler.display_name}) "
                "could not work with "
                f"Cluster of type ClusterType({cluster_with_mountpoint.cluster_type().id}, "
                f"{cluster_with_mountpoint.cluster_type().display_name}) or "
                f"Filesystem of type FilesystemType({filesystem.filesystem_type().id}, "
                f"{filesystem.filesystem_type().display_name})"
            ]
        }
