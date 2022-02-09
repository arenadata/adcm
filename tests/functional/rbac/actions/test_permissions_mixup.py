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

"""Test corner cases where permissions got messed up and allows more than they should be"""

from typing import Iterable, Tuple

import allure
import pytest
from adcm_client.objects import Cluster

from tests.functional.tools import AnyADCMObject
from tests.functional.rbac.conftest import (
    RbacRoles,
    is_allowed,
    as_user_objects,
    is_denied,
    BusinessRole,
)
from tests.functional.rbac.actions.utils import action_business_role, create_action_policy

pytestmark = [pytest.mark.extra_rbac]

SAME_DISPLAY_ACTION_NAME = "same_display"
DO_NOTHING_ACTION_NAME = "Do nothing"


class TestClusterAdminRoleDoNotBreakParametrization:
    """Test that granting "Cluster Administrator" role doesn't break parametrization of other objects"""

    # pylint: disable=no-self-use

    @pytest.fixture()
    def clusters(self, actions_cluster_bundle, simple_cluster_bundle) -> Tuple[Cluster, Cluster, Cluster, Cluster]:
        """Prepare clusters from two bundles"""
        first_cluster = actions_cluster_bundle.cluster_create("First Cluster")
        second_cluster = actions_cluster_bundle.cluster_create("Second Cluster")
        first_another_bundle_cluster = simple_cluster_bundle.cluster_create("Another Bundle Cluster")
        second_another_bundle_cluster = simple_cluster_bundle.cluster_create("One More Another Bundle Cluster")
        return first_cluster, second_cluster, first_another_bundle_cluster, second_another_bundle_cluster

    @pytest.fixture()
    def clusters_with_services(self, actions_cluster_bundle, simple_cluster_bundle) -> Tuple[Cluster, Cluster]:
        """
        Prepare two clusters with services:
          - first from actions bundle with two services
          - second from simple bundle with one service
        """
        first_cluster = actions_cluster_bundle.cluster_create("First Cluster")
        first_cluster.service_add(name="actions_service")
        first_cluster.service_add(name="no_components")
        second_cluster = simple_cluster_bundle.cluster_create("Second Cluster")
        second_cluster.service_add(name="actions_service")
        return first_cluster, second_cluster

    @allure.issue("https://arenadata.atlassian.net/browse/ADCM-2557")
    def test_cluster_admin(self, clients, user, clusters):
        """
        Test that granting "Cluster Admin" to one cluster
        doesn't lead to unauthorized access to another cluster's actions
        """

        first_cluster, second_cluster, first_another_bundle_cluster, second_another_bundle_cluster = as_user_objects(
            clients.user, *clusters
        )
        # will create role for each cluster with same prototype
        same_display_role = action_business_role(first_cluster, SAME_DISPLAY_ACTION_NAME)
        do_nothing_role = action_business_role(second_cluster, DO_NOTHING_ACTION_NAME)

        clients.admin.policy_create(
            name="Cluster Admin for First Cluster",
            role=clients.admin.role(display_name=RbacRoles.ClusterAdministrator.value),
            objects=[first_cluster],
            user=[user],
        )

        self.check_permissions(
            "Check that Cluster Admin grants permission only on one cluster",
            allowed=((first_cluster, same_display_role), (first_cluster, do_nothing_role)),
            denied=(
                (second_cluster, same_display_role),
                (second_cluster, do_nothing_role),
                (first_another_bundle_cluster, do_nothing_role),
                (second_another_bundle_cluster, do_nothing_role),
            ),
        )

        create_action_policy(
            clients.admin, second_cluster, action_business_role(first_cluster, SAME_DISPLAY_ACTION_NAME), user=user
        )

        self.check_permissions(
            "Check that Cluster Admin and permission to run action works correctly",
            # we can reuse allowed and disallowed if init them as sets
            # so if you'll have time, make those sets and change them
            allowed=(
                (first_cluster, same_display_role),
                (first_cluster, do_nothing_role),
                (second_cluster, same_display_role),
            ),
            denied=(
                (second_cluster, do_nothing_role),
                (first_another_bundle_cluster, do_nothing_role),
                (second_another_bundle_cluster, do_nothing_role),
            ),
        )

        create_action_policy(
            clients.admin,
            first_another_bundle_cluster,
            action_business_role(first_cluster, DO_NOTHING_ACTION_NAME),
            user=user,
        )

        self.check_permissions(
            "Check that Cluster Admin does not grant access to another bundle's clusters actions",
            allowed=(
                (first_cluster, same_display_role),
                (first_cluster, do_nothing_role),
                (second_cluster, same_display_role),
                (first_another_bundle_cluster, do_nothing_role),
            ),
            denied=(
                (second_cluster, do_nothing_role),
                (first_another_bundle_cluster, same_display_role),
                (second_another_bundle_cluster, do_nothing_role),
                (second_another_bundle_cluster, same_display_role),
            ),
        )

    def test_service_admin(self, clients, clusters_with_services, user):
        """Test that granting "Service Admin" role doesn't interfere"""
        first_cluster, second_cluster = clusters_with_services
        first_service, second_service = as_user_objects(clients.user, *first_cluster.service_list())
        another_cluster_service, *_ = as_user_objects(clients.user, second_cluster.service())
        # will create role for each cluster with same prototype
        same_display_role = action_business_role(first_service, SAME_DISPLAY_ACTION_NAME)
        do_nothing_role = action_business_role(second_service, DO_NOTHING_ACTION_NAME)

        clients.admin.policy_create(
            name="Service Admin for First Cluster",
            role=clients.admin.role(display_name=RbacRoles.ServiceAdministrator.value),
            objects=[first_service],
            user=[user],
        )

        self.check_permissions(
            "Check that Service Admin role allows actions only on one service in one cluster",
            allowed=((first_service, do_nothing_role), (first_service, same_display_role)),
            denied=((second_service, do_nothing_role), (another_cluster_service, do_nothing_role)),
        )

        create_action_policy(
            clients.admin,
            second_service,
            action_business_role(second_service, DO_NOTHING_ACTION_NAME),
            user=user,
        )

        self.check_permissions(
            "Check that granting permission for a single action on another service in cluster "
            "doesn't allow full access to cluster's actions",
            allowed=(
                (first_service, do_nothing_role),
                (first_service, same_display_role),
                (second_service, do_nothing_role),
            ),
            denied=((second_service, same_display_role), (another_cluster_service, do_nothing_role)),
        )

        create_action_policy(
            clients.admin,
            another_cluster_service,
            action_business_role(another_cluster_service, DO_NOTHING_ACTION_NAME),
            user=user,
        )

        self.check_permissions(
            "Check that granting permission to run a single action on another cluster's service "
            "doesn't grant extra permissions",
            allowed=(
                (first_service, do_nothing_role),
                (first_service, same_display_role),
                (second_service, do_nothing_role),
                (another_cluster_service, do_nothing_role),
            ),
            denied=((second_service, same_display_role), (another_cluster_service, same_display_role)),
        )

    def check_permissions(
        self,
        message: str,
        allowed: Iterable[Tuple[AnyADCMObject, BusinessRole]],
        denied: Iterable[Tuple[Cluster, BusinessRole]],
    ):
        """Check that permissions on actions works as expected"""
        with allure.step(message):
            for adcm_object, role in allowed:
                is_allowed(adcm_object, role).wait()
            for adcm_object, role in denied:
                is_denied(adcm_object, role)
