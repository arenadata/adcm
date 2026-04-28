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
    def get_ordering_cases(self) -> list[tuple]:
        """
        Return ordering cases as tuples of:

        an ordering parameter, a response value path, an expected (asc) result.
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


class TasksTestCase(BaseTestCase):
    def get_url(self) -> APINode:
        return self.suite.client.v2 / "tasks"

    def get_filters_cases(self) -> list:
        return [
            ("id", "id", self.suite.task_cl_1.pk, [self.suite.task_cl_1.pk], 0),
            ("name", "name", "B_TA", ["b_task"], "wrong"),  # check icontains
            ("displayName", "displayName", "A TA", ["A task"], "wrong"),  # check icontains
            ("status", "status", "success", ["success"], "failed"),
            # "objectName" sorting is performed by the annotated target_name so task ids are used for validation
            ("objectName", "id", "ALPH", [self.suite.task_cl_1.pk], "wrong"),  # check icontains
            ("objectName", "id", "A Service", [self.suite.task_service_1.pk], "service_1"),  # check mapping target_name
        ]

    def get_ordering_cases(self) -> list:
        return [
            ("id", "id", [self.suite.task_cl_1.pk, self.suite.task_service_1.pk, self.suite.task_hp_1.pk]),
            ("name", "name", ["a_task", "b_task", "c_task"]),
            ("displayName", "displayName", ["A task", "B task", "C task"]),
            ("startTime", "name", ["a_task", "b_task", "c_task"]),
            ("endTime", "name", ["a_task", "b_task", "c_task"]),
            ("status", "status", ["created", "created", "success"]),
            ("duration", "name", ["c_task", "b_task", "a_task"]),
            # "objectName" sorting is performed by the annotated target_name so task ids are used for validation
            ("objectName", "id", [self.suite.task_cl_1.id, self.suite.task_service_1.id, self.suite.task_hp_1.id]),
        ]
