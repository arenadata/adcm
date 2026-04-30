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

from abc import abstractmethod
from dataclasses import dataclass

from tests.client import APINode
from tests.suites import ADCMFiltersDataSuite


@dataclass(slots=True)
class BaseTestCase:
    suite: ADCMFiltersDataSuite

    @abstractmethod
    def get_url(self) -> APINode:
        """
        Return the url used by this case.
        """

    @abstractmethod
    def get_filters_cases(self) -> list[tuple]:
        """
        Return filter cases as tuples of:

        a filter parameter, a response value path, a filter value, a value of the expected result,
        a mismatch value.
        """

    @abstractmethod
    def get_choices_filters_cases(self) -> list[tuple]:
        """
        Return filter cases for choices fields as tuples of:

        a filter parameter, a response value path, a filter value, a value of the expected result.
        """

    @abstractmethod
    def get_ordering_cases(self) -> list[tuple]:
        """
        Return ordering cases as tuples of:

        an ordering parameter, a response value path, an expected (asc) result, an optional expected (desc) result.
        """


class BundlesTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "bundles"

    def get_filters_cases(self) -> list:
        return [
            ("id", "id", self.suite.bundle_cl_1.pk, [self.suite.bundle_cl_1.pk], "0"),
            ("displayName", "displayName", "A CLU", ["A Cluster", "A Cluster"], "wrong"),
            ("edition", "edition", "enterprise", ["enterprise"], "ent"),
            ("version", "version", "1.0.1", ["1.0.1"], "1"),
            ("mainPrototypeLicenseStatus", "mainPrototype.license.status", "accepted", ["accepted"], "unaccepted"),
            (
                "product",
                "mainPrototype.name",
                "B_CLUSTER",
                ["b_cluster"],
                "b_clus",
            ),
            ("signatureStatus", "signatureStatus", "valid", ["valid"], "invalid"),
        ]

    def get_ordering_cases(self) -> list:
        return [
            (
                "displayName",
                "displayName",
                ["A Cluster", "A Cluster", "A Provider", "A Provider", "B Cluster", "B Provider"],
            ),
            (
                "uploadTime",
                # product names are used as stable values to avoid coupling this case to the time format
                "name",
                ["a_cluster", "a_cluster", "b_cluster", "a_provider", "a_provider", "b_provider"],
            ),
            ("version", "version", ["1.0.0", "1.0.1", "12.0.0", "12.0.1", "2.0.0", "2.0.1"]),
            ("edition", "edition", ["community", "community", "community", "community", "community", "enterprise"]),
            (
                "mainPrototypeLicenseStatus",
                "mainPrototype.license.status",
                ["absent", "absent", "absent", "absent", "absent", "accepted"],
            ),
            ("signatureStatus", "signatureStatus", ["absent", "absent", "absent", "absent", "absent", "valid"]),
        ]


class ClustersTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "clusters"

    def get_filters_cases(self) -> list:
        return [
            ("id", "id", self.suite.cl_1.pk, [self.suite.cl_1.pk], "0"),
            ("name", "name", "HAcl", ["AlphaCl"], "wrong"),
            ("prototypeName", "prototype.name", "a_cluster", ["a_cluster", "a_cluster"], "wrong"),
            (
                "prototypeDisplayName",
                "prototype.displayName",
                "A Cluster",
                ["A Cluster", "A Cluster"],
                "wrong",
            ),
            ("state", "state", "installed", ["installed"], "wrong"),
            ("prototypeVersion", "prototype.version", "1.0.1", ["1.0.1"], "1"),
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("name", "name", ["AlphaCl", "BettaCl", "GammaCl"]),
            ("prototypeName", "prototype.name", ["a_cluster", "a_cluster", "b_cluster"]),
            (
                "prototypeDisplayName",
                "prototype.displayName",
                ["A Cluster", "A Cluster", "B Cluster"],
            ),
            ("prototypeVersion", "prototype.version", ["1.0.1", "12.0.0", "2.0.0"]),
            ("state", "state", ["created", "created", "installed"]),
        ]


class HostProvidersTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "hostproviders"

    def get_filters_cases(self) -> list:
        return [
            ("name", "name", "opro", ["FooProvider"], "wrong"),  # check icontains
            ("prototypeName", "prototype.name", "a_provider", ["a_provider", "a_provider"], "a_pro"),  # check exact
            (
                "prototypeDisplayName",
                "prototype.displayName",
                "A Provider",
                ["A Provider", "A Provider"],
                "A Pro",  # check exact
            ),
            ("state", "state", "installed", ["installed"], "wrong"),
            ("prototypeVersion", "prototype.version", "2.0.1", ["2.0.1"], "2"),  # check exact
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("name", "name", ["BarProvider", "FizzProvider", "FooProvider"]),
            ("prototypeName", "prototype.name", ["a_provider", "a_provider", "b_provider"]),
            (
                "prototypeDisplayName",
                "prototype.displayName",
                ["A Provider", "A Provider", "B Provider"],
            ),
            ("prototypeVersion", "prototype.version", ["1.0.0", "12.0.1", "2.0.1"]),
            ("state", "state", ["created", "created", "installed"]),
        ]


class ServicesTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2[self.suite.cl_1, "services"]

    def get_filters_cases(self) -> list:
        return [
            ("name", "name", "CE_1", ["service_1"], "wrong"),  # check icontains
            ("displayName", "displayName", "A SE", ["A Service", "A Service"], "wrong"),  # check icontains
            ("prototypeVersion", "prototype.version", "1.0.0", ["1.0.0"], "1"),  # check exact
            ("state", "state", "installed", ["installed"], "inst"),  # check exact
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("displayName", "displayName", ["A Service", "A Service", "B Service"]),
            ("prototypeVersion", "prototype.version", ["1.0.0", "12.0.1", "2.0.1"]),
            ("state", "state", ["created", "created", "installed"]),
            ("id", "id", [self.suite.service_1.pk, self.suite.service_2.pk, self.suite.service_3.pk]),
        ]


class ComponentsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2[self.suite.cl_1, "services", self.suite.service_1, "components"]

    def get_filters_cases(self) -> list:
        return [
            ("name", "name", "NT_1", ["component_1"], "wrong"),  # check icontains
            ("displayName", "displayName", "NT 1", ["Component 1"], "wrong"),  # check icontains
            ("id", "id", self.suite.comp_1.pk, [self.suite.comp_1.pk], "0"),
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("name", "name", ["component_1", "component_2", "component_3"]),
            ("displayName", "displayName", ["Component 1", "Component 2", "Component 3"]),
            ("id", "id", [self.suite.comp_1.pk, self.suite.comp_2.pk, self.suite.comp_3.pk]),
        ]


class HostsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "hosts"

    def get_filters_cases(self) -> list:
        return [
            ("name", "name", "st1", ["Host1"], "wrong"),  # check icontains
            (
                "hostproviderName",
                "hostprovider.name",
                "FooProvider",
                ["FooProvider"],
                "prov",  # check exact
            ),
            (
                "clusterName",
                "cluster.name",
                "AlphaCl",
                ["AlphaCl", "AlphaCl"],
                "clus",
            ),  # check exact
            ("state", "state", "installed", ["installed"], "ins"),  # check exact
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("id", "id", [self.suite.host_1.pk, self.suite.host_2.pk, self.suite.host_3.pk, self.suite.host_4.pk]),
            ("name", "name", ["Host1", "Host2", "Host3", "Host4"]),
            ("state", "state", ["created", "created", "created", "installed"]),
            ("hostproviderName", "hostprovider.name", ["BarProvider", "BarProvider", "FizzProvider", "FooProvider"]),
            ("clusterName", "cluster.name", ["AlphaCl", "AlphaCl", "GammaCl", None]),
        ]


class ClusterHostsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2[self.suite.cl_1, "hosts"]

    def get_filters_cases(self) -> list:
        return [
            ("name", "name", "st1", ["Host1"], "wrong"),  # check icontains
            (
                "hostproviderName",
                "hostprovider.name",
                "FooProvider",
                ["FooProvider"],
                "prov",  # check exact
            ),
            ("componentId", "components.id", self.suite.comp_1.pk, [self.suite.comp_1.pk], 0),
            ("componentName", "components.name", "component_1", ["component_1"], "comp"),  # check exact
            ("componentDisplayName", "components.displayName", "Component 1", ["Component 1"], "Comp"),  # check exact
            ("state", "state", "created", ["created"], "cre"),  # check exact
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("id", "id", [self.suite.host_1.pk, self.suite.host_2.pk]),
            ("name", "name", ["Host1", "Host2"]),
            ("state", "state", ["created", "installed"]),
            ("hostproviderName", "hostprovider.name", ["BarProvider", "FooProvider"]),
        ]


class AuditOperationsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "audit" / "operations"

    def get_filters_cases(self) -> list:
        return [
            ("id", "id", self.suite.audit_log_create_cluster.pk, [self.suite.audit_log_create_cluster.pk], 0),
            ("object_name", "object.name", "alph", ["AlphaCl"], "wrong"),
            ("object_type", "object.type", "provider", ["provider"], "adcm"),
            ("user_name", "user.name", "cluster", ["AdminClusterBobby", "AdminClusterBobby"], "wrong"),
            ("name", "name", "create_provider", ["create_provider"], "wrong"),
            ("result", "result", "success", ["success"], "denied"),
            ("type", "type", "update", ["update"], "delete"),
            (
                "time_from",
                "id",
                self.suite.matched_time_from_value,
                [self.suite.audit_log_create_provider_fail.pk, self.suite.audit_log_update_service.pk],
                self.suite.empty_match_time_from_value,
            ),
            (
                "time_to",
                "id",
                self.suite.matched_time_to_value,
                [self.suite.audit_log_create_cluster.pk],
                self.suite.empty_match_time_to_value,
            ),
        ]

    def get_ordering_cases(self) -> list[tuple]:
        return [
            ("objectName", "object.name", ["AlphaCl", "FooProvider", "service_1"]),
            ("objectType", "object.type", ["cluster", "provider", "service"]),
            ("name", "name", ["create_cluster", "create_provider", "update_service"]),
            ("type", "type", ["create", "create", "update"]),
            ("result", "result", ["fail", "fail", "success"]),
            ("userName", "user.name", ["AdminClusterBobby", "AdminClusterBobby", "ProviderAdminPeter"]),
            (
                "time",
                "id",
                [
                    self.suite.audit_log_create_cluster.pk,
                    self.suite.audit_log_update_service.pk,
                    self.suite.audit_log_create_provider_fail.pk,
                ],
            ),
        ]


class AuditLoginsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "audit" / "logins"

    def get_filters_cases(self) -> list:
        return [
            ("id", "id", self.suite.audit_login_success_cluster.pk, [self.suite.audit_login_success_cluster.pk], 0),
            ("user_name", "user.name", "ProviderAdminPeter", ["ProviderAdminPeter"], "wrong"),
            ("details_username", "details.username", "invis", [self.suite.non_existent_user_name], "missing"),
            ("result", "result", "user not found", ["user not found"], "account disabled"),
            (
                "time_from",
                "id",
                self.suite.matched_time_from_value,
                [self.suite.audit_login_user_not_found.pk, self.suite.audit_login_wrong_password.pk],
                self.suite.empty_match_time_from_value,
            ),
            (
                "time_to",
                "id",
                self.suite.matched_time_to_value,
                [self.suite.audit_login_success_cluster.pk],
                self.suite.empty_match_time_to_value,
            ),
        ]

    def get_ordering_cases(self) -> list[tuple]:
        return [
            (
                "loginTime",
                "id",
                [
                    self.suite.audit_login_success_cluster.pk,
                    self.suite.audit_login_wrong_password.pk,
                    self.suite.audit_login_user_not_found.pk,
                ],
            ),
            (
                "userName",
                "user.name",
                [
                    "AdminClusterBobby",
                    "ProviderAdminPeter",
                    None,
                ],
            ),
            ("result", "result", ["success", "user not found", "wrong password"]),
            (
                "time",
                "id",
                [
                    self.suite.audit_login_success_cluster.pk,
                    self.suite.audit_login_wrong_password.pk,
                    self.suite.audit_login_user_not_found.pk,
                ],
            ),
        ]


class UsersTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "rbac" / "users"

    def get_filters_cases(self) -> list[tuple]:
        return [
            ("username", "username", "AdMiN", ["admin"], "wrong"),
            ("username", "username", "TESTUSER", ["TestUser1"], "wrong"),
            ("email", "username", "testuser1@example.com", ["TestUser1"], "wrong"),
            ("groupDisplayName", "username", "Group1", ["TestUser1"], "wrong"),
            ("groupName", "username", "Group1 [local]", ["TestUser1"], "wrong"),
        ]

    def get_choices_filters_cases(self) -> list[tuple]:
        return [
            ("type", "username", "ldap", ["TestUser1"]),
            ("type", "username", "local", ["admin"]),
            ("status", "username", "active", ["admin"]),
            ("status", "username", "blocked", ["TestUser1"]),
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("username", "username", ["admin", "TestUser1"]),
            ("status", "username", ["admin", "TestUser1"]),
            ("email", "username", ["admin", "TestUser1"]),
            ("type", "username", ["TestUser1", "admin"]),
        ]

    @property
    def usernames_to_keep(self) -> list[str]:
        return ["admin", "TestUser1"]


class GroupsTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "rbac" / "groups"

    def get_filters_cases(self) -> list[tuple]:
        return [
            ("name", "displayName", "TestGroup [local]", ["TestGroup"], "wrong"),
            ("displayName", "displayName", "TestGroup", ["LDAPTestGroup", "TestGroup"], "wrong"),
            ("userUsername", "displayName", "admin", ["TestGroup"], "wrong"),
            ("userUsername", "displayName", "ADMIN", [], "wrong"),
        ]

    def get_choices_filters_cases(self) -> list[tuple]:
        return [
            ("type", "displayName", "local", ["Group1", "TestGroup"]),
            ("type", "displayName", "ldap", ["LDAPTestGroup"]),
        ]

    def get_ordering_cases(self) -> list[tuple]:
        return [
            ("name", "displayName", ["Group1", "LDAPTestGroup", "TestGroup"]),
            ("displayName", "displayName", ["Group1", "LDAPTestGroup", "TestGroup"]),
            ("type", "type", ["ldap", "local", "local"]),
        ]


class RolesTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "rbac" / "roles"

    def get_filters_cases(self) -> list[tuple]:
        return [
            ("name", "displayName", "Cluster Administrator", ["Cluster Administrator"], "wrong"),
            (
                "displayName",
                "displayName",
                "administrator",
                ["Cluster Administrator", "Service Administrator"],
                "wrong",
            ),
        ]

    def get_choices_filters_cases(self) -> list[tuple]:
        return [
            ("type", "displayName", "business", ["Add hosts to the Cluster"]),
            (
                "type",
                "displayName",
                "role",
                ["Cluster Administrator", "CustomRole", "CustomRoleAnyCategory", "Service Administrator"],
            ),
        ]

    def get_ordering_cases(self) -> list[tuple]:
        return [
            ("name", "displayName", ["Cluster Administrator", "Add hosts to the Cluster"]),
            ("displayName", "displayName", ["Add hosts to the Cluster", "Cluster Administrator"]),
            ("type", "displayName", ["Add hosts to the Cluster", "Cluster Administrator"]),
        ]

    @property
    def display_names_to_keep_filtering(self) -> list[str]:
        return [
            "Add hosts to the Cluster",
            "Cluster Administrator",
            "Service Administrator",
            "CustomRole",
            "CustomRoleAnyCategory",
        ]

    @property
    def display_names_to_keep_ordering(self) -> list[str]:
        return [
            "Add hosts to the Cluster",
            "Cluster Administrator",
        ]


class PoliciesTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "rbac" / "policies"

    def get_filters_cases(self) -> list[tuple]:
        return [
            ("id", "name", self.suite.policy.pk, ["CustomPolicy"], 0),
            ("name", "name", "CustomPolicy", ["CustomPolicy"], "wrong"),
            ("group_name", "name", "TestGroup [local]", ["ClusterPolicy", "ServicePolicy"], "wrong"),
            ("group_display_name", "name", "Group1", ["CustomPolicy"], "wrong"),
            ("role_name", "name", "Map hosts", ["ClusterPolicy"], "wrong"),
            ("role_display_name", "name", "CustomRole", ["CustomPolicy"], "wrong"),
            ("object_name", "name", "service_1", ["ServicePolicy"], "wrong"),
            ("object_display_name", "name", "A Service", ["ServicePolicy"], "wrong"),
        ]

    def get_ordering_cases(self) -> list[tuple]:
        return [
            ("name", "name", ["ClusterPolicy", "CustomPolicy", "ServicePolicy"]),
            ("roleName", "name", ["CustomPolicy", "ClusterPolicy", "ServicePolicy"]),
            ("roleDisplayName", "name", ["ClusterPolicy", "CustomPolicy", "ServicePolicy"]),
        ]
