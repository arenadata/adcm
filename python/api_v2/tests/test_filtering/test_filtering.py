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

from cm.legacy.services.status.client import FullStatusMap
from rbac.models import Role, User
from tests.client import APINode
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMFiltersDataSuite
from tests.utils import extract_from_nested_structure

from api_v2.tests.test_filtering.cases import (
    AuditLoginsTestCase,
    AuditOperationsTestCase,
    BundlesTestCase,
    ClusterHostsTestCase,
    ClustersTestCase,
    ComponentsTestCase,
    GroupsTestCase,
    HostProvidersTestCase,
    HostsTestCase,
    PoliciesTestCase,
    RolesTestCase,
    ServicesTestCase,
    UsersTestCase,
)


class FiltersBaseCheck(ADCMFiltersDataSuite):
    def check_ordering(self, *, url: APINode, ordering_cases: list) -> None:
        for ordering_field, value_path, asc_expected_value in ordering_cases:
            with self.subTest(direction="asc", ordering_field=ordering_field):
                results = self.get_results(url, value_path, query={"ordering": ordering_field})
                self.assertEqual(asc_expected_value, results)

            with self.subTest(direction="desc", ordering_field=ordering_field):
                results = self.get_results(url, value_path, query={"ordering": f"-{ordering_field}"})
                self.assertEqual(list(reversed(asc_expected_value)), results)

    def check_filters(self, *, url: APINode, filters_cases: list) -> None:
        for (
            filter_field,
            value_path,
            matched_query_value,
            matched_expected_value,
            empty_query_value,
        ) in filters_cases:
            with self.subTest(filter_result="matched", filter_field=filter_field):
                results = self.get_results(url, value_path, query={filter_field: matched_query_value})
                self.assertEqual(matched_expected_value, results)

            with self.subTest(filter_result="empty", filter_field=filter_field):
                results = self.get_results(url, value_path, query={filter_field: empty_query_value})
                self.assertEqual([], results)

    def check_choices_filters(self, *, url: APINode, filters_cases: list):
        for filter_field, response_value_path, filter_value, expected_value in filters_cases:
            with self.subTest(filter_result="matched_choice", filter_field=filter_field, filter_value=filter_value):
                results = self.get_results(url, response_value_path, query={filter_field: filter_value})
                self.assertEqual(expected_value, results)

    def check_filter_status(self, *, url: APINode, checked_status: str) -> None:
        """
        Check the filter by the status parameter.

        This method is implemented separately from the other filters for the following reasons:
        1. The parameter can only have two values: "up" and "down". In this case,
            checking for an empty list is not a filtering check.
        2. All status value settings for tests are located in one place and will
            only be set for this test.
        """

        status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(self.cl_1.pk): {
                        "services": {
                            str(self.service_1.pk): {
                                "status": 0,
                                "components": {},
                                "details": [],
                            },
                        },
                        "status": 0,
                        "hosts": {},
                    },
                }
            }
        )

        manager = get_status_scenarios_manager()
        manager.set_status_map(status_map)

        response = self.get_r(url=url, query={"status": checked_status})
        result = extract_from_nested_structure(response["results"], "status")

        expected_value = [checked_status]
        self.assertEqual(expected_value, result)


class TestAPIFilters(FiltersBaseCheck):
    """
    The class with tests for checking API filters and sorting.

    Each test declares a test case related to the target entity and one of four methods
    for checks: check_ordering, check_filters, check_choices_filters, check_filter_status.

    The method name consists: test_{check name}_{entity name}.

    If you want to add a special test, the name should be:
        test_{check name}_{entity name}_{feature}.
    """

    maxDiff = None

    def test_filters_clusters(self) -> None:
        case = ClustersTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_clusters(self) -> None:
        case = ClustersTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filter_status_clusters(self) -> None:
        case = ClustersTestCase(self)
        self.check_filter_status(url=case.get_url(), checked_status="up")

    def test_filters_bundles(self) -> None:
        case = BundlesTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_bundles(self) -> None:
        case = BundlesTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_hostproviders(self) -> None:
        case = HostProvidersTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_hostproviders(self) -> None:
        case = HostProvidersTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_services(self) -> None:
        case = ServicesTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_services(self) -> None:
        case = ServicesTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filter_status_services(self) -> None:
        case = ServicesTestCase(self)
        self.check_filter_status(url=case.get_url(), checked_status="up")

    def test_filters_components(self) -> None:
        case = ComponentsTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_components(self) -> None:
        case = ComponentsTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_hosts(self) -> None:
        case = HostsTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

        # Parameter isInCluster is boolean and the empty list of the response is not expected
        filter_field = "isInCluster"
        with self.subTest(filter_result="matched", filter_field=filter_field):
            response = self.get_r(url=case.get_url(), query={filter_field: False})
            result = extract_from_nested_structure(response["results"], "id")
            expected_value = [self.host_4.pk]
            self.assertListEqual(expected_value, result)

    def test_ordering_hosts(self) -> None:
        case = HostsTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_cluster_hosts(self) -> None:
        case = ClusterHostsTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_cluster_hosts(self) -> None:
        case = ClusterHostsTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_audit_operations(self) -> None:
        case = AuditOperationsTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_audit_operations(self) -> None:
        case = AuditOperationsTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filters_audit_logins(self) -> None:
        case = AuditLoginsTestCase(self)
        self.check_filters(
            url=case.get_url(),
            filters_cases=case.get_filters_cases(),
        )

    def test_ordering_audit_logins(self) -> None:
        case = AuditLoginsTestCase(self)
        self.check_ordering(
            url=case.get_url(),
            ordering_cases=case.get_ordering_cases(),
        )

    def test_filtering_users(self) -> None:
        case = UsersTestCase(self)
        User.objects.exclude(username__in=case.usernames_to_keep).delete()

        self.check_filters(url=case.get_url(), filters_cases=case.get_filters_cases())
        self.check_choices_filters(url=case.get_url(), filters_cases=case.get_choices_filters_cases())

    def test_ordering_users(self) -> None:
        case = UsersTestCase(self)
        User.objects.exclude(username__in=case.usernames_to_keep).delete()

        self.check_ordering(url=case.get_url(), ordering_cases=case.get_ordering_cases())

    def test_filtering_groups(self) -> None:
        case = GroupsTestCase(self)
        self.check_filters(url=case.get_url(), filters_cases=case.get_filters_cases())
        self.check_choices_filters(url=case.get_url(), filters_cases=case.get_choices_filters_cases())

    def test_ordering_groups(self) -> None:
        case = GroupsTestCase(self)
        self.check_ordering(url=case.get_url(), ordering_cases=case.get_ordering_cases())

    def test_filtering_roles(self) -> None:
        case = RolesTestCase(self)
        Role.objects.exclude(display_name__in=case.display_names_to_keep_filtering).delete()

        self.check_filters(url=case.get_url(), filters_cases=case.get_filters_cases())
        self.check_choices_filters(url=case.get_url(), filters_cases=case.get_choices_filters_cases())

    def test_filtering_roles_categories_field(self) -> None:
        """Special case. any_category=True Roles are shown either way"""

        case = RolesTestCase(self)
        Role.objects.exclude(display_name__in=case.display_names_to_keep_filtering).delete()

        filter_field = "categories"
        expected_roles = ["Add hosts to the Cluster", "CustomRole", "CustomRoleAnyCategory"]
        results = self.get_results(url=case.get_url(), value_path="displayName", query={filter_field: "TestCategory"})
        self.assertEqual(results, expected_roles)

        expected_roles = ["Add hosts to the Cluster", "CustomRoleAnyCategory"]
        results = self.get_results(
            url=case.get_url(), value_path="displayName", query={filter_field: "non-existent-category"}
        )
        self.assertEqual(results, expected_roles)

    def test_ordering_roles(self) -> None:
        case = RolesTestCase(self)
        Role.objects.exclude(display_name__in=case.display_names_to_keep_ordering).delete()

        self.check_ordering(url=case.get_url(), ordering_cases=case.get_ordering_cases())

    def test_filtering_policies(self) -> None:
        case = PoliciesTestCase(self)
        self.check_filters(url=case.get_url(), filters_cases=case.get_filters_cases())

    def test_ordering_policies(self) -> None:
        case = PoliciesTestCase(self)
        self.check_ordering(url=case.get_url(), ordering_cases=case.get_ordering_cases())
