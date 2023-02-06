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

"""Test permissions on actions behavior during upgrade"""

# pylint: disable=redefined-outer-name

from typing import Dict, Iterable, List, Literal, Tuple

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied, ObjectNotFound
from adcm_client.objects import ADCMClient, Bundle, Cluster, Component, Policy, Service
from adcm_client.wrappers.api import AccessIsDenied
from tests.functional.rbac.action_role_utils import (
    action_business_role,
    create_action_policy,
    get_action_display_name_from_role_name,
)
from tests.functional.rbac.actions.conftest import DATA_DIR
from tests.functional.rbac.checkers import ForbiddenCallChecker
from tests.functional.rbac.conftest import (
    BusinessRole,
    as_user_objects,
    is_allowed,
    is_denied,
)
from tests.functional.tools import ClusterRelatedObject
from tests.library.consts import HTTPMethod

ClusterObjectClassName = Literal["Cluster", "Service", "Component"]

NO_RIGHTS_ACTION = "No Rights"
NEW_ACTION = "New Job"
ACTION_TO_BE_DELETED = "Soon I Will Be Gone"
CHANGED_ACTION_NAME = "New Display Name"
ACTION_NAME_BEFORE_CHANGE = "Old Display Name"
MIMIC_NAME = "Whoops"


@pytest.fixture()
def old_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle with "old" version of cluster"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "upgrade" / "old"))


@pytest.fixture()
def old_cluster(old_bundle) -> Cluster:
    """Create "old" version of cluster"""
    cluster = old_bundle.cluster_create(name="Test cluster to upgrade")
    cluster.service_add(name="servicemaster")
    return cluster


@pytest.fixture()
def new_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle with "new" version of cluster"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "upgrade" / "new"))


class TestActionRolesOnUpgrade:
    """Test how permissions work before and after upgrade"""

    NOT_ALLOWED_ACTIONS = (NO_RIGHTS_ACTION, NEW_ACTION, CHANGED_ACTION_NAME)

    @pytest.fixture()
    def old_cluster_objects(self, old_cluster) -> Tuple[Cluster, Service, Component]:
        """Get cluster, service and component from old cluster as admin objects"""
        return old_cluster, (service := old_cluster.service()), service.component()

    @pytest.fixture()
    def old_cluster_objects_map(self, old_cluster_objects) -> Dict[ClusterObjectClassName, ClusterRelatedObject]:
        """Get old cluster objects as map"""
        return self._get_objects_map(old_cluster_objects)

    @pytest.fixture()
    def all_business_roles(self, old_cluster_objects):
        """Build roles for all actions on all objects both before and after the upgrade"""
        return [
            action_business_role(adcm_object, action_display_name, no_deny_checker=True)
            for adcm_object in old_cluster_objects
            for action_display_name in (
                *(a.display_name for a in adcm_object.action_list()),
                NEW_ACTION,
                CHANGED_ACTION_NAME,
            )
        ]

    @pytest.fixture()
    def old_cluster_actions_policies(self, clients, user, all_business_roles, old_cluster_objects_map) -> List[Policy]:
        """
        Grant permissions to run all actions on cluster, service and component for a user except:
        1. "No Rights" action.
        2. Actions that'll appear after upgrade or will be renamed (for obvious reasons).
        """
        return [
            create_action_policy(
                clients.admin,
                self._get_object_from_map_by_role_name(role.role_name, old_cluster_objects_map),
                role,
                user=user,
            )
            for role in self._get_roles_filter_exclude_by_action_name(all_business_roles, self.NOT_ALLOWED_ACTIONS)
        ]

    @pytest.mark.usefixtures("new_bundle", "old_cluster_actions_policies")
    def test_upgrade(self, clients, user, old_cluster, all_business_roles, old_cluster_objects_map):
        """
        Test that upgrade works correctly considering permissions on actions:
        1. Actions with same name and display name are still available after upgrade if permissions were granted.
        2. Display name change leads to denying of previously granted permission.
        3. Policy on new action can be created and will be allowed if granted.
        """
        self.check_permissions_before_upgrade(clients.user, all_business_roles, old_cluster_objects_map)
        new_cluster = self.upgrade_cluster(old_cluster)
        self.check_permissions_after_upgrade(clients.user, all_business_roles, old_cluster_objects_map)
        self.check_action_with_changed_display_name_not_allowed_by_name(clients.user, old_cluster_objects_map)
        self.check_new_action_can_be_launched(clients, user, new_cluster)
        self.check_new_action_with_old_display_name(clients.user, old_cluster_objects_map)

    @allure.step("Check permissions working as expected before upgrade")
    def check_permissions_before_upgrade(self, user_client: ADCMClient, all_business_roles, object_map):
        """Check that correct permissions are allowed/denied before cluster upgrade"""
        self.check_roles_are_allowed(
            user_client,
            object_map,
            tuple(self._get_roles_filter_exclude_by_action_name(all_business_roles, self.NOT_ALLOWED_ACTIONS)),
        )
        self.check_roles_are_denied(
            user_client,
            object_map,
            tuple(self._get_roles_filter_select_by_action_name(all_business_roles, (NO_RIGHTS_ACTION,))),
        )

    @allure.step("Upgrade cluster")
    def upgrade_cluster(self, cluster):
        """Upgrade cluster and reread it"""
        cluster.upgrade().do()
        cluster.reread()
        return cluster

    @allure.step("Check permissions working as expected after upgrade")
    def check_permissions_after_upgrade(self, user_client: ADCMClient, all_business_roles, user_object_map):
        """Check that correct permissions are allowed/denied after cluster upgrade"""
        self.check_roles_are_allowed(
            user_client,
            user_object_map,
            tuple(
                self._get_roles_filter_exclude_by_action_name(
                    all_business_roles,
                    (ACTION_NAME_BEFORE_CHANGE, ACTION_TO_BE_DELETED, *self.NOT_ALLOWED_ACTIONS),
                )
            ),
        )

        self.check_roles_are_denied(
            user_client,
            user_object_map,
            tuple(self._get_roles_filter_select_by_action_name(all_business_roles, self.NOT_ALLOWED_ACTIONS)),
        )

    @allure.step("Check action with changed display name isn't available for user")
    def check_action_with_changed_display_name_not_allowed_by_name(self, user_client, object_map):
        """Check that action with changed display name can't be launched by its name"""
        cluster, *_ = as_user_objects(user_client, object_map["Cluster"])
        try:
            cluster.action(name="alternative_display_name").run()
        except (AccessIsDenied, NoSuchEndpointOrAccessIsDenied, ObjectNotFound):
            pass
        else:
            raise AssertionError("Action that changed display name shouldn't be allowed to run")

    @allure.step("Check that new action in bundle can be launched when policy is created")
    def check_new_action_can_be_launched(self, clients, user, upgraded_cluster: Cluster):
        """Check that policy can be created to run new action from cluster bundle and action actually can be launched"""
        service = upgraded_cluster.service()
        component = service.component()
        for adcm_object in upgraded_cluster, service, component:
            business_role = action_business_role(adcm_object, NEW_ACTION)
            create_action_policy(clients.admin, adcm_object, business_role, user=user)
            is_allowed(as_user_objects(clients.user, adcm_object)[0], business_role).wait()

    @allure.step('Check display_name based role works on "mimic" action')
    def check_new_action_with_old_display_name(self, user_client, user_object_map):
        """Check that new action that have display_name of another action from old version can be launched"""
        cluster = user_object_map["Cluster"]
        business_role = action_business_role(cluster, MIMIC_NAME)
        is_allowed(as_user_objects(user_client, cluster)[0], business_role)

    def check_roles_are_allowed(
        self,
        user_client: ADCMClient,
        cluster_object_map: Dict[ClusterObjectClassName, ClusterRelatedObject],
        business_roles: Iterable[BusinessRole],
    ):
        """Check that given roles are allowed to be launched"""
        for role in business_roles:
            adcm_object, *_ = as_user_objects(
                user_client,
                self._get_object_from_map_by_role_name(role.role_name, cluster_object_map),
            )
            is_allowed(adcm_object, role).wait()

    def check_roles_are_denied(
        self,
        user_client: ADCMClient,
        cluster_object_map: Dict[ClusterObjectClassName, ClusterRelatedObject],
        business_roles: Iterable[BusinessRole],
    ):
        """Check that given roles aren't allowed to be launched"""
        for role in business_roles:
            adcm_object = self._get_object_from_map_by_role_name(role.role_name, cluster_object_map)
            action_id = adcm_object.action(display_name=get_action_display_name_from_role_name(role.role_name)).id
            rule_with_denied = BusinessRole(
                role.role_name,
                role.method_call,
                ForbiddenCallChecker(adcm_object.__class__, f"action/{action_id}/run", HTTPMethod.POST),
            )
            is_denied(adcm_object, rule_with_denied, client=user_client)

    def _get_objects_map(self, objects):
        """Represent an object in form of an object map: { classname: object }"""
        return {obj.__class__.__name__: obj for obj in objects}

    def _get_object_from_map_by_role_name(self, action_business_role_name: str, objects_map):
        """Get object from map by object mentioned in action role name"""
        object_type = action_business_role_name.split()[0]
        try:
            return objects_map[object_type]
        except KeyError as e:
            raise KeyError(f"Object of type {object_type} was not found in objects map: {objects_map}") from e

    def _objects_map_as_user_objects(self, client, objects_map):
        """Convert objects in map to user's objects"""
        return {key: as_user_objects(client, obj)[0] for key, obj in objects_map.items()}

    @staticmethod
    def _get_roles_filter_exclude_by_action_name(business_roles, exclude_actions: Iterable[str]):
        """Filter roles by excluding the ones that have names listed in exclude_actions"""
        return filter(lambda r: all(name not in r.role_name for name in exclude_actions), business_roles)

    @staticmethod
    def _get_roles_filter_select_by_action_name(business_roles, include_actions: Iterable[str]):
        """Filter roles by including the ones that have names listed in include_actions"""
        return filter(lambda r: all(name in r.role_name for name in include_actions), business_roles)
