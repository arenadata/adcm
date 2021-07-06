"""
Common utils for functional tests
"""
import time
from typing import List

import allure
from adss_client.client import ADSSClient
from adss_client.exceptions import ObjectNotFound
from adss_client.objects import ClusterType, Handler, Cluster, Filesystem, JobQueue
from coreapi.exceptions import ErrorMessage

from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.fake_data import generate_json_from_schema
from tests.utils.tools import random_string

DEFAULT_HANDLER_THREADS = 1


@allure.step("Search for cluster type with name like {name_part}")
def get_cluster_type_by_name_part(name_part: str, adss_client: ADSSClient) -> ClusterType:
    """
    Get cluster type by cluster type name part
    """
    for c_type in adss_client.cluster_type_iter():
        if c_type.name.find(name_part) > -1:
            return c_type
    raise AssertionError(f"No cluster types with {name_part} in name found")


@allure.step("Create job queue for {cluster}")
def create_job_queue(
    adss_client: ADSSClient,
    cluster: Cluster,
    filesystem: Filesystem,
    threads=DEFAULT_HANDLER_THREADS,
) -> JobQueue:
    """
    Create Job Queue with generated config by schema with default threads for functional tests
    """
    handler = next(iter(adss_client.handler_iter()))
    generated_config = generate_json_from_schema(json_schema=handler.config_schema)
    generated_config["threads"] = threads
    return cluster.job_queue_create(
        name=f"jobqueue-{random_string()}",
        filesystem=filesystem,
        handler=handler,
        config=generated_config,
    )


@allure.step("Wait for Job Queue to complete")
def wait_end_job_queue(adss_client, job_queue, interval=1, timeout=300):
    """
    Wait for job queue to complete
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            adss_client.job_queue(id=job_queue.id)
        except ErrorMessage:
            break
        time.sleep(interval)
    else:
        raise AssertionError(f"Failed to wait for Job Queue to complete within {timeout} seconds")


@allure.step("Wait for Job Queue to appear")
def wait_appear_job_queue(adss_client, cron_name, interval=1, timeout=30):
    """
    Wait some job queue
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            return adss_client.job_queue(name=cron_name)
        except ObjectNotFound:
            time.sleep(interval)
            continue
    raise AssertionError(f"Failed to wait for Job Queue to appear within {timeout} seconds")


@allure.step("Wait for Job Queue go to state {state}")
def wait_job_queue_state(job_queue: JobQueue, state: str, interval=1, timeout=30):
    """
    Wait until job queue didn't appear some state
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            job_queue.reread()
            assert job_queue.state == state
        except AssertionError:
            time.sleep(interval)
            continue
        else:
            return
    raise AssertionError(
        f"Job queue did not change status from {job_queue.state} to {state} "
        f"with {timeout} seconds"
    )


@allure.step("Get unsupported handlers for create Job Queue to {cluster}")
def get_unsupported_handlers(adss_client: ADSSClient, cluster: Cluster) -> List[Handler]:
    """
    Get unsupported handlers for create Job Queue to Cluster
    """

    unsupported_handlers = []
    cluster_filesystem_type_ids = [
        mp.filesystem().filesystem_type().id for mp in cluster.mount_point_set()
    ]
    for handler in adss_client.handler_iter():
        handler_filesystem_type_ids = [fs.id for fs in handler.filesystem_type_set()]
        if not set(handler_filesystem_type_ids) & set(cluster_filesystem_type_ids):
            unsupported_handlers.append(handler)
    if not unsupported_handlers:
        raise ValueError(
            "No unsupported handlers found to create the Job Queue."
            f" May be using a different image from '{ADSS_DEV_IMAGE}'"
        )
    return unsupported_handlers
