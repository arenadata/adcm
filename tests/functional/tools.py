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
Common functions and helpers for testing ADCM
"""
import json
from typing import Callable, Collection, Dict, Iterable, List, Optional, Tuple, Union

import allure
import pytest
from _pytest.outcomes import Failed
from adcm_client.base import ObjectNotFound, PagingEnds
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    Group,
    GroupConfig,
    Host,
    Job,
    Policy,
    Provider,
    Role,
    Service,
    Task,
    User,
)
from adcm_pytest_plugin.docker_utils import ADCM, get_file_from_container
from adcm_pytest_plugin.utils import catch_failed, wait_until_step_succeeds
from coreapi.exceptions import ErrorMessage

BEFORE_UPGRADE_DEFAULT_STATE = None


ADCMObjects = (Cluster, Service, Component, Provider, Host)
RBACObjects = (User, Group, Role, Policy)

ClusterRelatedObject = Union[Cluster, Service, Component]
ProviderRelatedObject = Union[Provider, Host]
AnyADCMObject = Union[ClusterRelatedObject, ProviderRelatedObject, ADCMClient]
AnyRBACObject = Union[User, Group, Role, Policy]

DEFAULT_TIMEOUT = 20
DEFAULT_PERIOD = 2


def get_config(adcm_object: AnyADCMObject):
    """Get config or empty tuple (if config not defined)"""
    try:
        return adcm_object.config()
    except ErrorMessage:
        return ()


@allure.step("Wait all tasks are finished")
def wait_all_jobs_are_finished(client: ADCMClient):
    for job in client.job_list():
        job.task().wait()


def wait_for_job_status(
    job: Job,
    status: str = "running",
    timeout: Optional[int] = DEFAULT_TIMEOUT,
    period: Optional[int | float] = DEFAULT_PERIOD,
):
    def _wait():
        job.reread()
        assert job.status == status, f"Job {job.display_name} should be in status {status}"

    wait_until_step_succeeds(_wait, timeout=timeout, period=period)


@allure.step("Check object state")
def check_object_state(adcm_object: Cluster | Service | Component, expected_state: str) -> None:
    adcm_object.reread()
    actual = adcm_object.state
    assert actual == expected_state, f"Expected object state {expected_state} Actual {actual}"


@allure.step("Check object multi state")
def check_object_multi_state(adcm_object: Cluster | Service | Component, expected_state: list) -> None:
    adcm_object.reread()
    assert (
        len(adcm_object.multi_state) > 0
    ), f"Expected object does not have multi state while expected state: {expected_state}"
    for actual, expected in zip(adcm_object.multi_state, expected_state):
        assert actual == expected, f"Expected object multi state {actual} Actual object multi state{expected}"


@allure.step("Check jobs status")
def check_jobs_status(task: Task, expected_job_status: dict) -> None:
    task.reread()
    actual_jobs_status = {job.display_name: job.status for job in task.job_list()}
    assert len(actual_jobs_status) == len(expected_job_status), (
        f"Incorrect number of jobs. Actual jobs are: {len(actual_jobs_status)},"
        f" while expected jobs are: {len(expected_job_status)}"
    )
    assert actual_jobs_status == expected_job_status, (
        "Expected jobs are not equal with actual"
        f"\nExpected jobs: {expected_job_status}, actual jobs: {actual_jobs_status}"
    )


def get_objects_via_pagination(
    object_list_method: Callable, pagination_step: int = 20
) -> List[Union[AnyADCMObject, Job, Task]]:
    """Get all objects as a flat list using pagination"""

    def ignore_paging_ends(paging: dict) -> list:
        try:
            return list(object_list_method(paging=paging))
        except PagingEnds:
            # if previous request returned amount of objects equal to pagination_step
            # then request of new objects raises PagingEnds
            return []

    pagination = {'offset': 0, 'limit': pagination_step}
    objects = []
    while objects_on_next_page := ignore_paging_ends(pagination):
        objects.extend(objects_on_next_page)
        pagination['offset'] += pagination_step
        pagination['limit'] += pagination_step
    return objects


def action_in_object_is_present(action: str, obj: AnyADCMObject):
    """Assert action in object is present"""
    with allure.step(f"Assert that action {action} is present in {get_object_represent(obj)}"):
        with catch_failed(ObjectNotFound, f"Action {action} not found in object {obj}"):
            obj.action(name=action)


def actions_in_objects_are_present(actions_to_obj: List[Tuple[str, AnyADCMObject]]):
    """Assert actions in objects are present"""
    for pair in actions_to_obj:
        action_in_object_is_present(*pair)


def action_in_object_is_absent(action: str, obj: AnyADCMObject):
    """Assert action in object is absent"""
    with allure.step(f"Assert that action {action} is absent in {get_object_represent(obj)}"):
        with catch_failed(Failed, f"Action {action} is present in {get_object_represent(obj)}"):
            with pytest.raises(ObjectNotFound):
                obj.action(name=action)


def actions_in_objects_are_absent(actions_to_obj: List[Tuple[str, AnyADCMObject]]):
    """Assert actions in objects are absent"""
    for pair in actions_to_obj:
        action_in_object_is_absent(*pair)


def get_object_represent(obj: AnyADCMObject) -> str:
    """Get human readable object string"""
    return (
        f"host {obj.fqdn}"
        if isinstance(obj, Host)
        else f"{obj.__class__.__name__.lower()} {obj.name if hasattr(obj, 'name') else ''}"
    )


def create_config_group_and_add_host(
    group_name: str,
    object_with_group: Union[ClusterRelatedObject, Provider],
    *hosts: Iterable[Host],
) -> GroupConfig:
    """Create config group with given name and add all passed hosts"""
    with allure.step(f"Create config group '{group_name}' and add hosts: {' '.join((h.fqdn for h in hosts))}"):
        group = object_with_group.group_config_create(name=group_name)
        for host in hosts:
            group.host_add(host)
        return group


def get_inventory_file(adcm_fs: ADCM, task_id: int) -> dict:
    """Get inventory.json file from ADCM as dict"""
    file = get_file_from_container(adcm_fs, f'/adcm/data/run/{task_id}/', 'inventory.json')
    content = file.read().decode('utf8')
    return json.loads(content)


# !===== HC ACL builder =====!


def build_hc_for_hc_acl_action(
    cluster: Cluster,
    add: Collection[Tuple[Component, Host]] = (),
    remove: Collection[Tuple[Component, Host]] = (),
    add_new_bundle_components: Collection[Tuple[int, Host]] = (),
) -> List[Dict[str, int]]:
    """
    Build a `hc` argument for a `hc_acl` action run based on cluster's hostcomponent and add/remove "directives".
    Result contains only unique entries (because of the HC nature).
    """
    hostcomponent = {(hc['service_id'], hc['component_id'], hc['host_id']) for hc in cluster.hostcomponent()}
    to_remove = {(component.service_id, component.id, from_host.id) for component, from_host in remove}
    hostcomponent.difference_update(to_remove)
    to_add = {(component.service_id, component.id, to_host.id) for component, to_host in add}
    return [
        *[
            {'service_id': service_id, 'component_id': component_id, 'host_id': host_id}
            for service_id, component_id, host_id in (hostcomponent | to_add)
        ],
        *[
            {'component_prototype_id': component_proto_id, 'host_id': host.id}
            for component_proto_id, host in add_new_bundle_components
        ],
    ]


# LDAP


def check_user_is_active(user: User) -> None:
    """Check that user's `is_active` flag is True"""
    with allure.step(f"Check user {user.username} is active"):
        user.reread()
        assert user.is_active, "User should inactive"


def check_user_is_deactivated(user: User) -> None:
    """Check that user's `is_active` flag is False"""
    with allure.step(f"Check user {user.username} is inactive"):
        user.reread()
        assert not user.is_active, "User should be inactive"


def run_ldap_sync(client: ADCMClient) -> Task:
    """Run LDAP sync action"""
    return client.adcm().action(name="run_ldap_sync").run()
