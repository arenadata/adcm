"""
ADSS objects deletion tests
"""
# pylint: disable=redefined-outer-name, protected-access
import allure
import pytest

from coreapi.exceptions import ErrorMessage
from pytest_lazyfixture import lazy_fixture

from tests.functional.utils.common import wait_appear_job_queue

pytest_plugins = ["tests.functional.utils.fixtures"]
pytestmark = [
    allure.suite("Delete objects tests"),
]


def _assert_reference_error(error, deletable_obj, reference_obj):
    """
    Check error message about reference between objects
    """
    response_error_body = error.value.error._data  # pylint: disable=protected-access
    assert (
        response_error_body["desc"] == f"Object {deletable_obj.__class__.__name__} "
        "could not be deleted because it's referenced from others"
    )
    assert response_error_body["details"] == {
        reference_obj.__class__.__name__: [f'/api/v1/{reference_obj.PATH}/{reference_obj.id}/'],
        'model': deletable_obj.__class__.__name__,
    }


def test_filesystem_delete_positive(adss_client_fs, cluster_with_jobhistory):
    """
    Positive test for File System delete functional
    File System should be deleted with related Mount Point
    Job History’s File System links should have 'None' value
    """
    cluster, _ = cluster_with_jobhistory
    cluster.reread()
    created_filesystem = cluster.mount_point_set()[0].filesystem()
    with allure.step(f"Delete {created_filesystem} and assert success"):
        created_filesystem.delete()
        assert (
            len(list(adss_client_fs.filesystem_iter())) == 0
        ), "File System list not empty after delete"
        assert (
            len(list(adss_client_fs.mount_point_iter())) == 0
        ), "Mount Point list not empty after delete"
        assert (
            next(iter(adss_client_fs.job_history_iter())).filesystem() is None
        ), "Job History’s File System links not null"


@pytest.mark.parametrize(
    "created_cluster",
    [lazy_fixture("cluster_with_cronline"), lazy_fixture("cluster_with_jobqueue")],
)
def test_filesystem_delete_negative(created_cluster):
    """
    Negative test for File System delete functional
    Attempt to delete File System should fail because there is associated object
    """
    cluster, reference_obj = created_cluster
    cluster.reread()
    created_filesystem = cluster.mount_point_set()[0].filesystem()

    with allure.step(f"Delete {created_filesystem} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            created_filesystem.delete()
        _assert_reference_error(err, created_filesystem, reference_obj)


def test_cluster_delete_positive(adss_client_fs, cluster_with_jobhistory):
    """
    Positive test for Cluster delete functional
    Cluster should be deleted with related Mount Point
    Job History’s Cluster links should have 'None' value
    """
    cluster, _ = cluster_with_jobhistory
    with allure.step(f"Delete {cluster} and assert success"):
        cluster.delete()
        assert len(list(adss_client_fs.cluster_iter())) == 0, "Cluster list not empty after delete"
        assert (
            len(list(adss_client_fs.mount_point_iter())) == 0
        ), "Mount Point list not empty after delete"
        assert (
            next(iter(adss_client_fs.job_history_iter())).cluster() is None
        ), "Job History’s Cluster links not null"


@pytest.mark.parametrize(
    "created_cluster",
    [lazy_fixture("cluster_with_cronline"), lazy_fixture("cluster_with_jobqueue")],
)
def test_cluster_delete_negative(created_cluster):
    """
    Negative test for Cluster delete functional
    Attempt to delete Cluster should fail because there is associated object
    """
    cluster, referenced_obj = created_cluster
    with allure.step(f"Delete {cluster} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            cluster.delete()
        _assert_reference_error(err, cluster, referenced_obj)


def test_mountpoint_delete_positive(adss_client_fs, cluster_with_mountpoint):
    """
    Positive test for Mount Point delete functional
    """
    cluster = cluster_with_mountpoint
    cluster.reread()
    mount_point = cluster.mount_point_set()[0]
    with allure.step(f"Delete {mount_point} and assert success"):
        mount_point.delete()
        assert (
            len(list(adss_client_fs.mount_point_iter())) == 0
        ), "Mount Point list not empty after delete"


@pytest.mark.parametrize(
    "created_cluster",
    [lazy_fixture("cluster_with_cronline"), lazy_fixture("cluster_with_jobqueue")],
)
def test_mountpoint_delete_negative(created_cluster):
    """
    Negative test for Mount Point delete functional
    Attempt to delete Mount Point should fail because there is associated object
    """
    cluster, referenced_obj = created_cluster
    cluster.reread()
    mount_point = cluster.mount_point_set()[0]
    with allure.step(f"Delete {mount_point} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            mount_point.delete()
        _assert_reference_error(err, mount_point, referenced_obj)


def test_cronline_delete_positive(adss_client_fs, cluster_with_cronline):
    """
    Positive test for Cron Line delete functional
    """
    _, cronline = cluster_with_cronline
    with allure.step(f"Delete {cronline} and assert success"):
        cronline.delete()
        assert (
            len(list(adss_client_fs.cron_line_iter())) == 0
        ), "Cron Line list not empty after delete"


@pytest.mark.parametrize(
    "cluster_with_cronline", ["* * * * *"], ids=["EVERY_MINUTE_CRONLINE"], indirect=True
)
def test_cronline_delete_negative(adss_client_fs, cluster_with_cronline):
    """
    Negative test for Cron Line delete functional
    Attempt to delete Cron Line should fail because there is associated object
    """
    _, cronline = cluster_with_cronline
    job_queue = wait_appear_job_queue(adss_client_fs, cron_name=cronline.name, timeout=70)
    with allure.step(f"Delete {cronline} and assert fail"):
        with pytest.raises(ErrorMessage) as err:
            cronline.delete()
        _assert_reference_error(err, cronline, job_queue)
