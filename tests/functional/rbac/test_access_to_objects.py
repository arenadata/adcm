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
Test that granting any permission on object allows user to:
- see this object in the list of objects
- get this object from ADCM client
"""

import os.path
from collections.abc import Callable, Iterable
from contextlib import contextmanager

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    Group,
    Provider,
    Service,
    Task,
    User,
)
from adcm_pytest_plugin.utils import catch_failed
from coreapi.exceptions import ErrorMessage

from tests.functional.rbac.action_role_utils import (
    action_business_role,
    create_action_policy,
)
from tests.functional.rbac.conftest import DATA_DIR
from tests.functional.rbac.conftest import BusinessRoles as BR  # noqa: N817
from tests.functional.rbac.conftest import (
    RbacRoles,
    SDKClients,
    create_policy,
    delete_policy,
    get_as_client_object,
)
from tests.functional.tools import get_object_represent
from tests.library.utils import lower_class_name


@contextmanager
def granted_policy(client, business_role, adcm_object, user):
    """Create policy based on business role and delete if afterwards"""
    policy = create_policy(client, business_role, [adcm_object], [user], [])
    yield policy
    delete_policy(policy)


class TestAccessToBasicObjects:
    """
    Test granting access to default objects:
    cluster, service, component, provider, host
    """

    @pytest.mark.extra_rbac()  # pylint: disable-next=too-many-locals
    def test_access_to_cluster_from_service_role(self, clients, user, prepare_objects, second_objects):
        """
        Test that granting permission on service grants permission to "view" service and cluster
        """
        all_objects = prepare_objects + second_objects
        cluster, service, component, provider, host = prepare_objects
        not_viewable_objects = (component, provider, host) + second_objects
        cluster_and_service = (cluster, service)

        for business_role in (BR.VIEW_SERVICE_CONFIGURATIONS, BR.EDIT_SERVICE_CONFIGURATIONS, BR.VIEW_IMPORTS):
            objects_to_check = ", ".join(map(lower_class_name, cluster_and_service))
            with allure.step(
                f'Check that granting "{business_role.value.role_name}" role to service '
                f"gives view access to: {objects_to_check}",
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                with granted_policy(clients.admin, business_role, service, user):
                    check_objects_are_viewable(clients.user, cluster_and_service)
                    check_objects_are_not_viewable(clients.user, not_viewable_objects)
                check_objects_are_not_viewable(clients.user, all_objects)

    @pytest.mark.extra_rbac()
    def test_access_to_parents_from_component_role(self, clients, user, prepare_objects, second_objects):
        """
        Test that granting permission on component grants permission to "view" component, service and cluster
        """
        all_objects = prepare_objects + second_objects
        cluster, service, component, *provider_objects = prepare_objects
        cluster_objects = (cluster, service, component)

        for business_role in (BR.VIEW_COMPONENT_CONFIGURATIONS, BR.EDIT_COMPONENT_CONFIGURATIONS):
            with allure.step(
                f'Check that granting "{business_role.value.role_name}" role to component '
                'gives access to "view" cluster',
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                with granted_policy(clients.admin, business_role, component, user):
                    check_objects_are_viewable(clients.user, cluster_objects)
                    check_objects_are_not_viewable(clients.user, tuple(provider_objects) + second_objects)
                check_objects_are_not_viewable(clients.user, all_objects)

    @pytest.mark.extra_rbac()
    def test_hierarchy_access_to_host(self, clients, user, cluster_bundle, provider_bundle):
        """
        Test that user can get host
        when it is bonded to a cluster (user has permission to get this cluster),
        when host is added to a cluster
        when permission is granted before/after host is added
        """
        cluster = cluster_bundle.cluster_create(name="Test Cluster")
        provider = provider_bundle.provider_create(name="Test Provider")
        first_host, second_host = provider.host_create("host-1"), provider.host_create("host-2")

        with allure.step('Add host to a cluster and check "view" permissions are granted'):
            cluster.host_add(first_host)
            check_objects_are_not_viewable(clients.user, [first_host, second_host])

        with allure.step('Create policy on cluster and check "view" permission exists on added host'):
            policy = create_policy(clients.admin, BR.VIEW_HOST_COMPONENTS, [cluster], [user], [])
            check_objects_are_viewable(clients.user, [first_host])
            check_objects_are_not_viewable(clients.user, [second_host])

        with allure.step('Add second host and check "view" permission is granted on it'):
            cluster.host_add(second_host)
            check_objects_are_viewable(clients.user, [first_host, second_host])

        with allure.step('Remove first host and check "view" permission is withdrawn'):
            cluster.host_delete(first_host)
            check_objects_are_viewable(clients.user, [second_host])
            check_objects_are_not_viewable(clients.user, [first_host])

        with allure.step('Remove policy and check "view" permissions were withdrawn'):
            delete_policy(policy)
            check_objects_are_not_viewable(clients.user, [first_host, second_host])

    @pytest.mark.extra_rbac()
    def test_hostcomponent_set(self, clients, user, prepare_objects, second_objects):
        """
        Test that hostcomponent can be set via ADCM client: user can get component and hosts on cluster
        """
        cluster, service, component, provider, host = prepare_objects
        check_objects_are_not_viewable(clients.user, prepare_objects + second_objects)
        with granted_policy(clients.admin, BR.EDIT_HOST_COMPONENTS, cluster, user):
            cluster.host_add(host)
            check_objects_are_viewable(clients.user, [cluster, service, component, host])
            check_objects_are_not_viewable(clients.user, [provider] + list(second_objects))
        check_objects_are_not_viewable(clients.user, prepare_objects + second_objects)


class TestActionBasedAccess:
    """Test that granting permission to run action grants "view" permissions on an owner object"""

    @pytest.fixture()
    def cluster_with_host_action(self, sdk_client_fs):
        """Create cluster with host action"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "cluster_with_host_action"))
        return bundle.cluster_create(name="Cool Test Cluster")

    @pytest.fixture()
    def host(self, cluster_with_host_action, provider_bundle):
        """Host object from "regular" provider that is added to cluster with host action"""
        provider = provider_bundle.provider_create(name="Cool Test Provider")
        return cluster_with_host_action.host_add(provider.host_create("see-mee-with-action"))

    def test_action_permission_grants_access_to_owner_object(self, clients, user, prepare_objects, second_objects):
        """
        Test that permission on action of an object grants permission to "view" this object
        """
        objects = set(prepare_objects)
        another_objects = set(second_objects)
        all_objects = objects | another_objects

        for adcm_object in objects:
            with allure.step(
                f"Add permission to run action on {adcm_object.__class__.__name__} and check if it became visible",
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                policy = create_action_policy(
                    clients.admin,
                    adcm_object,
                    action_business_role(adcm_object, "No config action", no_deny_checker=True),
                    user=user,
                )
                check_objects_are_viewable(clients.user, [adcm_object])
                check_objects_are_not_viewable(
                    clients.user,
                    all_objects - self._get_object_and_parents_from_objects(adcm_object, all_objects),
                )
                delete_policy(policy)
                check_objects_are_not_viewable(clients.user, all_objects)

    def _get_object_and_parents_from_objects(self, adcm_object, objects) -> set:
        """
        Return set of object and its parents (if object is service or component) in set,
        otherwise return just object itself in set
        """
        if isinstance(adcm_object, Service):
            parent = next(obj for obj in objects if isinstance(obj, Cluster) and obj.id == adcm_object.cluster_id)
            return {adcm_object, parent}
        if isinstance(adcm_object, Component):
            parents = {
                obj
                for obj in objects
                if (isinstance(obj, Service) and obj.id == adcm_object.service_id)
                or (isinstance(obj, Cluster) and obj.id == adcm_object.cluster_id)
            }
            return parents | {adcm_object}
        return {adcm_object}

    @pytest.mark.extra_rbac()
    def test_host_action_permission_grants_access_to_owner_object(self, clients, user, host, prepare_objects):
        """
        Test that permission on host actions grants permission to "view" host
        """
        cluster = host.cluster()
        *other_objects, second_host = prepare_objects
        check_objects_are_not_viewable(clients.user, (cluster, host) + prepare_objects)
        policy = create_action_policy(
            clients.admin,
            cluster,
            action_business_role(cluster, "Host action", no_deny_checker=True),
            user=user,
        )
        check_objects_are_viewable(clients.user, [cluster, host])
        check_objects_are_not_viewable(clients.user, prepare_objects)
        cluster.host_add(second_host)
        check_objects_are_viewable(clients.user, [cluster, host, second_host])
        check_objects_are_not_viewable(clients.user, other_objects)
        with allure.step("Change host state and check nothing broke"):
            host.action(name="host_action").run().wait()
            check_objects_are_viewable(clients.user, [cluster, host])

        delete_policy(policy)
        check_objects_are_not_viewable(clients.user, [cluster, host])


class TestAccessForJobsAndLogs:
    """Test access for tasks, jobs, logs"""

    REGULAR_ACTION = "Regular action"
    MULTIJOB_ACTION = "Multijob"

    SERVICE_NAME = "test_service"

    @allure.title("Cluster with service")
    @pytest.fixture()
    def cluster(self, sdk_client_fs) -> Cluster:
        """Cluster with service"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "jobs", "cluster"))
        cluster = bundle.cluster_create("Test Cluster")
        cluster.service_add(name=self.SERVICE_NAME)
        return cluster

    @allure.title("Cluster without service")
    @pytest.fixture()
    def cluster_wo_service(self, cluster) -> Cluster:
        """Cluster without service"""
        cluster.service_delete(cluster.service())
        return cluster

    @allure.title("Cluster ready for upgrade")
    @pytest.fixture()
    def cluster_for_upgrade(self, sdk_client_fs) -> Cluster:
        """Cluster ready for upgrade"""
        path_to_upgrade_dir = os.path.join(os.path.dirname(__file__), "actions", "bundles", "upgrade")
        old = sdk_client_fs.upload_from_fs(os.path.join(path_to_upgrade_dir, "old"))
        sdk_client_fs.upload_from_fs(os.path.join(path_to_upgrade_dir, "new"))
        return old.cluster_create("Test Cluster for Upgrade")

    @allure.title("Provider with host")
    @pytest.fixture()
    def provider(self, sdk_client_fs):
        """Provider with host"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "jobs", "provider"))
        provider = bundle.provider_create("Test Provider")
        provider.host_create("test-host")
        return provider

    @pytest.fixture()
    def finished_tasks(self, cluster, provider) -> list[Task]:
        """Bunch of finished tasks"""
        tasks = []
        service = cluster.service()
        for adcm_object in (cluster, service, service.component(), provider, provider.host()):
            task = adcm_object.action(display_name=self.REGULAR_ACTION).run()
            tasks.append(task)
            task.wait()
        return tasks

    @pytest.fixture(params=["user", "group"], ids=["with_user", "with_group"])
    def user_or_group(self, request, user, clients) -> dict[str, User | Group]:
        """Return user or group"""

        if request.param == "user":
            return {"user": user}
        if request.param == "group":
            return {"group": clients.admin.group_create(name="somegroup", user=[{"id": user.id}])}
        raise ValueError('param should be either "user" or "group"')

    # pylint: disable-next=too-many-locals
    def test_access_to_tasks(self, user_or_group: dict, clients, cluster, provider, finished_tasks):
        """
        Test that user:
        1. Have no access to task objects that were launched before user got permission to run action
        2. Have access to task objects of allowed actions launched by all users after permission is granted
        3. Have no access to task objects after policy deletion
        """
        service = cluster.service()
        user_api = clients.user._api  # pylint: disable=protected-access
        new_tasks = []

        # add normal allure steps here
        self.check_no_access_granted_for_tasks(clients.user, finished_tasks)
        for adcm_object in (cluster, service, service.component(), provider, provider.host()):
            with allure.step(
                f'Create policy for running action "{self.MULTIJOB_ACTION}" on {adcm_object.__class__.__name__}',
            ):
                policy = create_action_policy(
                    clients.admin,
                    adcm_object,
                    action_business_role(adcm_object, self.MULTIJOB_ACTION, no_deny_checker=True),
                    **user_or_group,
                )
                user_object = get_as_client_object(user_api, adcm_object)
                user_task = user_object.action(display_name=self.MULTIJOB_ACTION).run()
                user_task.wait()
                admin_multijob = adcm_object.action(display_name=self.MULTIJOB_ACTION).run()
                admin_multijob.wait()
                admin_regular_task = adcm_object.action(display_name=self.REGULAR_ACTION).run()
                admin_regular_task.wait()
                new_tasks.extend((user_task, admin_multijob, admin_regular_task))
                self.check_access_granted_for_tasks(clients.user, [user_task, admin_multijob])
                self.check_no_access_granted_for_tasks(clients.user, finished_tasks + [admin_regular_task])
                delete_policy(policy)
                self.check_no_access_granted_for_tasks(clients.user, new_tasks + finished_tasks)

    @pytest.mark.extra_rbac()
    def test_access_to_tasks_on_service_add_remove(
        self,
        user_or_group: dict,
        cluster_wo_service: Cluster,
        clients: SDKClients,
    ):
        """
        Test that service add/remove doesn't break permission to view task objects:
        1. Add service
        2. Create policy on action
        3. Run action and check access to task objects is granted
        4. Remove service and expect access remains
        5. Add service again
        6. Run action and check access to task objects of both tasks is granted
        """
        cluster = cluster_wo_service
        service = cluster.service_add(name=self.SERVICE_NAME)
        create_action_policy(
            clients.admin,
            service,
            action_business_role(service, self.REGULAR_ACTION, no_deny_checker=True),
            **user_or_group,
        )
        with allure.step("Run action and check access to task objects"):
            task = _run_and_wait(service, self.REGULAR_ACTION)
            self.check_access_granted_for_tasks(clients.user, [task])
        with allure.step("Delete service and check that access remains"):
            cluster.service_delete(service)
            self.check_access_granted_for_tasks(clients.user, [task])
        with allure.step("Add service again"):
            service = cluster.service_add(name=self.SERVICE_NAME)
        with allure.step("Run action one more time and check access denied to both tasks"):
            second_task = service.action(display_name=self.REGULAR_ACTION).run()
            second_task.wait()
            self.check_access_granted_for_tasks(clients.user, [task])
            self.check_no_access_granted_for_tasks(clients.user, [second_task])

    @pytest.mark.extra_rbac()
    def test_access_to_tasks_on_cluster_host_add_remove(
        self,
        user_or_group: Callable,
        cluster: Cluster,
        provider: Provider,
        clients: SDKClients,
    ):
        """
        Test that access to task objects is correct after host add/remove from cluster
        """
        host = provider.host()
        create_action_policy(
            clients.admin,
            host,
            action_business_role(host, self.REGULAR_ACTION, no_deny_checker=True),
            **user_or_group,
        )
        with allure.step("Run action and check that access is granted"):
            task = _run_and_wait(host, self.REGULAR_ACTION)
            self.check_access_granted_for_tasks(clients.user, [task])
        with allure.step("Add host to cluster, run action and check access to tasks"):
            cluster.host_add(host)
            second_task = _run_and_wait(host, self.REGULAR_ACTION)
            self.check_access_granted_for_tasks(clients.user, [task, second_task])
        with allure.step("Remove host from cluster and check access to task objects"):
            cluster.host_delete(host)
            self.check_access_granted_for_tasks(clients.user, [task, second_task])

    @pytest.mark.extra_rbac()
    def test_access_to_tasks_on_hc_map_change(self, user_or_group: dict, cluster, provider, clients):
        """
        Test that access for task objects is correct after HC map is changed
        """
        host = provider.host()
        component = cluster.service().component()
        with allure.step("Create permission to run action on host and component"):
            for adcm_object in (host, component):
                create_action_policy(
                    clients.admin,
                    adcm_object,
                    action_business_role(adcm_object, self.REGULAR_ACTION, no_deny_checker=True),
                    **user_or_group,
                )
        with allure.step("Run actions and check access to them"):
            host_task = _run_and_wait(host, self.REGULAR_ACTION)
            component_task = _run_and_wait(component, self.REGULAR_ACTION)
            self.check_access_granted_for_tasks(clients.user, [host_task, component_task])
        with allure.step("Set HC map and check access to task objects"):
            cluster.host_add(host)
            cluster.hostcomponent_set((host, component))
            second_host_task = _run_and_wait(host, self.REGULAR_ACTION)
            second_component_task = _run_and_wait(component, self.REGULAR_ACTION)
            self.check_access_granted_for_tasks(
                clients.user,
                [host_task, component_task, second_host_task, second_component_task],
            )
        with allure.step("Change HC map and check access to task objects"):
            second_host = provider.host_create("second-host")
            cluster.host_add(second_host)
            cluster.hostcomponent_set((second_host, component))
            self.check_access_granted_for_tasks(
                clients.user,
                [host_task, component_task, second_host_task, second_component_task],
            )

    @pytest.mark.extra_rbac()
    def test_access_for_jobs_after_upgrade(self, cluster_for_upgrade, clients, user):
        """
        Test that access to task objects stays after the upgrade
        """
        cluster = cluster_for_upgrade
        with granted_policy(
            clients.admin,
            clients.admin.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value),
            cluster,
            user,
        ):
            with allure.step("Run actions and check task objects are available"):
                tasks = [_run_and_wait(cluster, action.display_name) for action in cluster.action_list()]
                self.check_access_granted_for_tasks(clients.user, tasks)
            with allure.step("Upgrade cluster and check task objects are still available"):
                cluster.upgrade().do()
                self.check_access_granted_for_tasks(clients.user, tasks)
            with allure.step("Run actions after upgrade and check that all task objects are available"):
                tasks.extend(_run_and_wait(cluster, action.display_name) for action in cluster.action_list())
                self.check_access_granted_for_tasks(clients.user, tasks)

    def test_roles_that_give_access_to_tasks(self, cluster, provider, clients, user):
        """
        Test that all roles that should give access to task objects truly grant it
        """
        service = cluster.service()
        component = service.component()
        host = provider.host()

        with allure.step(
            f"Check role {RbacRoles.CLUSTER_ADMINISTRATOR.value} grants access to task objects of "
            "cluster, service, component and host",
        ):
            role = clients.admin.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value)
            cluster.host_add(host)
            with granted_policy(clients.admin, role, cluster, user):
                tasks = [_run_and_wait(obj, self.REGULAR_ACTION) for obj in (cluster, service, component, host)]
                self.check_access_granted_for_tasks(clients.user, tasks)
            self.check_no_access_granted_for_tasks(clients.user, tasks)
            cluster.host_delete(host)

        with allure.step(
            f"Check role {RbacRoles.SERVICE_ADMINISTRATOR.value} "
            f"grants access to task objects of service and component",
        ):
            role = clients.admin.role(name=RbacRoles.SERVICE_ADMINISTRATOR.value)
            with granted_policy(clients.admin, role, service, user):
                tasks = [_run_and_wait(obj, self.REGULAR_ACTION) for obj in (service, component)]
                self.check_access_granted_for_tasks(clients.user, tasks)
            self.check_no_access_granted_for_tasks(clients.user, tasks)

        with allure.step(
            f"Check role {RbacRoles.PROVIDER_ADMINISTRATOR.value} grants access to task objects of provider and host",
        ):
            role = clients.admin.role(name=RbacRoles.PROVIDER_ADMINISTRATOR.value)
            with granted_policy(clients.admin, role, provider, user):
                tasks = [_run_and_wait(obj, self.REGULAR_ACTION) for obj in (provider, host)]
                self.check_access_granted_for_tasks(clients.user, tasks)
            self.check_no_access_granted_for_tasks(clients.user, tasks)

    def test_access_after_one_of_two_action_permissions_is_removed(self, clients, user, cluster):
        """
        Test that when:
        1. Permissions to run two actions are granted to user
        2. User launched both actions
        3. Permission on one of actions is withdrawn
        User should be able to see logs of the permitted action
        """
        with allure.step("Grant user two policies on different actions on cluster"):
            create_action_policy(
                clients.admin,
                cluster,
                action_business_role(cluster, self.REGULAR_ACTION, no_deny_checker=True),
                user=user,
            )
            multijob_policy = create_action_policy(
                clients.admin,
                cluster,
                action_business_role(cluster, self.MULTIJOB_ACTION, no_deny_checker=True),
                user=user,
            )
        with allure.step("Run both allowed actions"):
            regular_task = _run_and_wait(cluster, self.REGULAR_ACTION)
            multijob_task = _run_and_wait(cluster, self.MULTIJOB_ACTION)
        with allure.step("Check that user have access for both tasks"):
            self.check_access_granted_for_tasks(clients.user, [regular_task, multijob_task])
        with allure.step(
            'Delete policy on "multijob" and check that user now have access right only on "regular" task',
        ):
            delete_policy(multijob_policy)
            self.check_access_granted_for_tasks(clients.user, [regular_task])
            self.check_no_access_granted_for_tasks(clients.user, [multijob_task])

    def check_access_granted_for_tasks(self, user_client: ADCMClient, tasks: Iterable[Task]):
        """Check that access is granted to tasks, their jobs and logs"""
        client_username = user_client.me().username
        api = user_client._api  # pylint: disable=protected-access
        with allure.step(f'Check that user "{client_username}" has no access for certain tasks, jobs and logs'):
            for task in tasks:
                with catch_failed(ObjectNotFound, "Task object should be available directly via client"):
                    get_as_client_object(api, task)
                for job in task.job_list():
                    with catch_failed(ObjectNotFound, "Job and log objects should be available directly via client"):
                        get_as_client_object(api, job)
                        get_as_client_object(api, job.log(), path_args={"job_pk": job.id})

    def check_no_access_granted_for_tasks(self, user_client: ADCMClient, tasks: Iterable[Task]):
        """Check there's no access to tasks, their jobs and logs"""
        client_username = user_client.me().username
        api = user_client._api  # pylint: disable=protected-access
        with allure.step(f'Check that user "{client_username}" has no access for certain tasks, jobs and logs'):
            for task in tasks:
                _expect_not_found(api, task, "Task object should not be available directly via client")
                for job in task.job_list():
                    _expect_not_found(api, job, "Job object should be available directly via client")
                    log = job.log()
                    _expect_not_found(
                        api,
                        log,
                        "Log object should be available directly via client",
                        path_args={"job_pk": job.id},
                    )


def _get_objects_id(get_objects_list: Callable) -> set[int]:
    return {obj.id for obj in get_objects_list()}


def _expect_not_found(api, obj, message, **kwargs):
    try:
        get_as_client_object(api, obj, **kwargs)
    except ErrorMessage as e:
        if not hasattr(e.error, "title") or e.error.title != "404 Not Found":
            raise AssertionError(message) from e
    else:
        raise AssertionError(message)


def check_objects_are_viewable(user_client: ADCMClient, objects):
    """Check that user can see objects in list and get them by id"""
    client_username = user_client.me().username
    api = user_client._api  # pylint: disable=protected-access
    with allure.step(f'Check that certain objects are viewable to user "{client_username}"'):
        for adcm_object in objects:
            object_represent = get_object_represent(adcm_object)
            with allure.step(f'Check that "{object_represent}" is available to user {client_username}'):
                object_type_name = lower_class_name(adcm_object)
                list_objects = getattr(user_client, f"{object_type_name}_list")
                available_objects_ids = _get_objects_id(list_objects)
                assert (
                    adcm_object.id in available_objects_ids
                ), f'Object "{object_represent}" should be listed in the list of {object_type_name}s'
                with catch_failed(
                    ObjectNotFound,
                    f'Object "{object_represent}" should be available directly via client',
                ):
                    get_as_client_object(api, adcm_object)


def check_objects_are_not_viewable(user_client: ADCMClient, objects):
    """Check that user can't see objects in list and get them by id"""
    client_username = user_client.me().username
    api = user_client._api  # pylint: disable=protected-access
    with allure.step(f'Check that certain objects are not viewable to user "{client_username}"'):
        for adcm_object in objects:
            object_represent = get_object_represent(adcm_object)
            with allure.step(f'Check that "{object_represent}" is not available to user {client_username}'):
                object_type_name = lower_class_name(adcm_object)
                list_objects = getattr(user_client, f"{object_type_name}_list")
                available_objects_ids = _get_objects_id(list_objects)
                assert (
                    adcm_object.id not in available_objects_ids
                ), f'Object "{object_represent}" should not be listed in the list of {object_type_name}s'
                _expect_not_found(
                    api,
                    adcm_object,
                    f'Object "{object_represent}" should not be available directly via client',
                )


def _run_and_wait(adcm_object, action_display_name) -> Task:
    task = adcm_object.action(display_name=action_display_name).run()
    task.wait()
    return task
