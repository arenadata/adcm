"""ADSS functional tests fixtures"""
# pylint: disable=redefined-outer-name
from typing import Tuple

import allure
import pytest
from adss_client.objects import Cluster, CronLine, JobQueue, JobHistory, Filesystem

from tests.functional.utils.common import (
    get_cluster_type_by_name_part,
    wait_end_job_queue,
    create_job_queue,
    DEFAULT_HANDLER_THREADS,
)
from tests.utils.fake_data import generate_json_from_schema
from tests.utils.tools import random_string


CRON_LINE_TEST_VALUE = "0 0 1 * *"


@allure.step("Create Cluster")
@pytest.fixture()
def cluster(adss_client_fs) -> Cluster:
    """
    Create Cluster
    """
    adb_cluster_type = get_cluster_type_by_name_part(name_part="ADB", adss_client=adss_client_fs)

    cluster = adb_cluster_type.cluster_create(
        name=f"ADB-{random_string()}",
        connection=generate_json_from_schema(json_schema=adb_cluster_type.connection_schema),
    )

    return cluster


@allure.step("Create dummy cluster")
@pytest.fixture()
def dummy_cluster(adss_client_fs) -> Cluster:
    """
    Create cluster using dummy cluster type
    """
    adb_cluster_type = adss_client_fs.cluster_type(name="dummy_cluster_type")

    cluster = adb_cluster_type.cluster_create(
        name=f"Dummy-{random_string(5)}",
        connection=generate_json_from_schema(json_schema=adb_cluster_type.connection_schema),
    )
    return cluster


@allure.step("Create Filesystem")
@pytest.fixture()
def filesystem(adss_client_fs) -> Filesystem:
    """
    Create Filesystem
    """
    filesystem_type = next(iter(adss_client_fs.filesystem_type_iter()))
    filesystem = filesystem_type.filesystem_create(
        name=f"filesystem-{random_string()}",
        connection=generate_json_from_schema(json_schema=filesystem_type.connection_schema),
    )

    return filesystem


@allure.step("Create dummy filesystem")
@pytest.fixture()
def dummy_filesystem(adss_client_fs) -> Filesystem:
    """
    Create filesystem using dummy filesystem type
    """
    filesystem_type = adss_client_fs.filesystem_type(name="dummy_filesystem_type")
    filesystem = filesystem_type.filesystem_create(
        name=f"dummy-fs-{random_string(5)}",
        connection=generate_json_from_schema(json_schema=filesystem_type.connection_schema),
    )
    return filesystem


@allure.step("Create Cluster with Mount Point")
@pytest.fixture()
def cluster_with_mountpoint(cluster, filesystem) -> Cluster:
    """
    Create Cluster with Mount Point
    """
    cluster.mount_point_create(
        filesystem=filesystem,
        connection=generate_json_from_schema(
            json_schema=filesystem.filesystem_type().mount_point_schema
        ),
    )

    return cluster


@allure.step("Create dummy cluster with Mount Point")
@pytest.fixture()
def dummy_cluster_with_mountpoint(dummy_cluster, dummy_filesystem) -> Cluster:
    """
    Create dummy cluster with Mount Point
    """
    dummy_cluster.mount_point_create(
        filesystem=dummy_filesystem,
        connection=generate_json_from_schema(
            json_schema=dummy_filesystem.filesystem_type().mount_point_schema
        ),
    )

    return dummy_cluster


@allure.step("Create Cluster with Job Queue")
@pytest.fixture()
def cluster_with_jobqueue(adss_client_fs, cluster_with_mountpoint) -> Tuple[Cluster, JobQueue]:
    """
    Prepare cluster with Job Queue
    """
    cluster = cluster_with_mountpoint
    cluster.reread()
    filesystem = cluster.mount_point_set()[0].filesystem()

    with allure.step(f"Set all capacity for {cluster} to 0"):
        for capacity in cluster.cluster_capacity_set():
            capacity.value = 0
            capacity.save()

    job_queue = create_job_queue(adss_client_fs, cluster, filesystem)

    return cluster, job_queue


@allure.step("Create Cluster with Job History")
@pytest.fixture()
def cluster_with_jobhistory(adss_client_fs, cluster_with_mountpoint) -> Tuple[Cluster, JobHistory]:
    """
    Prepare Cluster with Job Queue
    """
    cluster = cluster_with_mountpoint
    cluster.reread()
    filesystem = cluster.mount_point_set()[0].filesystem()

    job_queue = create_job_queue(adss_client_fs, cluster, filesystem)

    wait_end_job_queue(adss_client_fs, job_queue)
    job_history = adss_client_fs.job_history(id=job_queue.id)

    return cluster, job_history


@allure.step("Create Cluster with Cron Line")
@pytest.fixture(params=[CRON_LINE_TEST_VALUE], ids=["EVERY_HOUR_CRONLINE"])
def cluster_with_cronline(
    request, adss_client_fs, cluster_with_mountpoint
) -> Tuple[Cluster, CronLine]:
    """
    Prepare Cluster with Cron Line
    """
    cluster = cluster_with_mountpoint
    cluster.reread()
    filesystem = cluster.mount_point_set()[0].filesystem()

    with allure.step(f"Set all capacity for {cluster} to 0"):
        for capacity in cluster.cluster_capacity_set():
            capacity.value = 0
            capacity.save()

    with allure.step(f"Create cron line for {cluster}"):
        handler = next(iter(adss_client_fs.handler_iter()))
        generated_config = generate_json_from_schema(json_schema=handler.config_schema)
        generated_config["threads"] = DEFAULT_HANDLER_THREADS
        cron_line = cluster.cron_line_create(
            name=f"cronline-{random_string()}",
            filesystem=filesystem,
            handler=handler,
            config=generated_config,
            cron_line=request.param,
        )
    return cluster, cron_line
