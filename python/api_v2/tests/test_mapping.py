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

from pathlib import Path

from cm.models import (
    Action,
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConfigHostGroup,
    Host,
    HostComponent,
    MaintenanceMode,
    Service,
    Upgrade,
)
from django.db.models import F
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_409_CONFLICT,
)
from tests.suites import ADCMDjangoAPISuite

from api_v2.tests.base import APIV2Mixin, TestUtilsMixin


class TestMapping(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="test_host_B", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="test_host_A", cluster=cls.cluster_1)
        cls.host_3 = cls.uc.add_host(provider=cls.provider, fqdn="test_host_C", cluster=cls.cluster_2)

        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)[0]
        cls.component_1 = Component.objects.get(service=cls.service_1, prototype__name="component_1")
        cls.component_2 = Component.objects.get(service=cls.service_1, prototype__name="component_2")
        cls.component_3 = Component.objects.get(service=cls.service_1, prototype__name="component_3")

        cls.uc.set_hostcomponent(cluster=cls.cluster_1, entries=[(cls.host_1, cls.component_1)])

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def test_list_mapping_success(self):
        response = self.client.v2[self.cluster_1, "mapping"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertDictEqual(
            response.json()[0],
            HostComponent.objects.filter(cluster_id=self.cluster_1.id).values(
                "id", componentId=F("component_id"), hostId=F("host_id")
            )[0],
        )

    def test_create_mapping_success(self):
        host_4 = self.add_host(provider=self.provider, fqdn="test_host_4")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_4)
        data = [
            {"hostId": host_4.pk, "componentId": self.component_2.pk},
            {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
        ]

        response = self.client.v2[self.cluster_1, "mapping"].post(data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 2)

    def test_permissions_mapping_host_another_cluster_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View imports"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Cluster Administrator"):
                data = [
                    {"hostId": self.host_2.pk, "componentId": self.component_1.pk},
                ]
                response = self.client.v2[self.cluster_1, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_permissions_mapping_host_another_cluster_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            data = [
                {"hostId": self.host_2.pk, "componentId": self.component_1.pk},
            ]
            response = self.client.v2[self.cluster_1, "mapping"].post(data=data)

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_and_object_permissions_mapping_host_another_cluster_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View imports"):
                with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Cluster Administrator"):
                    response = self.client.v2[self.cluster_1, "mapping"].post(
                        data=[
                            {"hostId": self.host_2.pk, "componentId": self.component_1.pk},
                        ]
                    )

                    self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_mapping_host_another_cluster_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View imports"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Cluster Administrator"):
                response = self.client.v2[self.cluster_1, "mapping"].get()

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_model_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            response = self.client.v2[self.cluster_1, "mapping"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_object_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View host-components"):
            response = self.client.v2[self.cluster_1, "mapping"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_model_permissions_mapping_host_another_cluster_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object import"):
            response = self.client.v2[self.cluster_1, "mapping"].get()

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_and_object_permissions_mapping_host_another_cluster_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object import"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View imports"):
                with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Cluster Administrator"):
                    response = self.client.v2[self.cluster_1, "mapping"].get()

                    self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_create_mapping_duplicates_fail(self):
        host_4 = self.add_host(provider=self.provider, fqdn="test_host_4", cluster=self.cluster_1)

        data = [
            {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
            {"hostId": self.host_1.pk, "componentId": self.component_1.pk},  # duplicate h1 c1
            {"hostId": self.host_1.pk, "componentId": self.component_1.pk},  # another duplicate h1 c1
            {"hostId": self.host_2.pk, "componentId": self.component_2.pk},
            {"hostId": self.host_2.pk, "componentId": self.component_2.pk},  # duplicate h2 c2
            {"hostId": self.host_2.pk, "componentId": self.component_2.pk},  # another duplicate h2 c2
            {"hostId": host_4.pk, "componentId": self.component_1.pk},
        ]

        duplicate_ids = (
            (self.host_1.pk, self.component_1.pk, self.component_1.service.pk),
            (self.host_2.pk, self.component_2.pk, self.component_2.service.pk),
        )
        error_msg_part = ", ".join(f"component {map_ids[1]} - host {map_ids[0]}" for map_ids in sorted(duplicate_ids))

        response = self.client.v2[self.cluster_1, "mapping"].post(data=data)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "INVALID_INPUT",
                "level": "error",
                "desc": f"Mapping entries duplicates found: {error_msg_part}.",
            },
        )

    def test_create_empty_mapping_success(self):
        response = self.client.v2[self.cluster_1, "mapping"].post(data=[])

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_mapping_hosts_success(self):
        response = self.client.v2[self.cluster_1, "mapping", "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()
        self.assertEqual(len(response), 2)
        self.assertEqual({host["id"] for host in response}, {self.host_1.pk, self.host_2.pk})
        # check sort by fqdn
        self.assertListEqual([h["name"] for h in response], sorted([self.host_1.fqdn, self.host_2.fqdn]))

    def test_mapping_components_success(self):
        response = self.client.v2[self.cluster_1, "mapping", "components"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)
        self.assertEqual(
            {component["id"] for component in response.json()},
            {self.component_1.pk, self.component_2.pk, self.component_3.pk},
        )

    def test_mapping_components_with_requires_success(self):
        bundle = self.uc.upload_bundle(src=self.test_bundles_dir / "cluster_requires_component")
        cluster = self.uc.add_cluster(bundle=bundle, name="cluster_requires")
        self.uc.add_services_to_cluster(names=["hbase", "zookeeper", "hdfs"], cluster=cluster)

        response = self.client.v2[cluster, "mapping", "components"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 3)

        for component_data in data:
            component = Component.objects.filter(prototype__name=component_data["name"], cluster=cluster).first()

            if not component.prototype.requires:
                self.assertIsNone(component_data["dependOn"])
                continue

            self.assertEqual(len(component.prototype.requires), len(component_data["dependOn"]))


class TestMappingConstraints(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "hc_mapping_constraints")
        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle, name="cluster_with_hc_requirements")
        second_cluster = cls.uc.add_cluster(bundle=cluster_bundle, name="second_cluster")

        provider = cls.uc.add_provider(bundle=provider_bundle, name="provider")

        cls.host_not_in_cluster = cls.uc.add_host(provider=provider, fqdn="host_not_in_cluster")
        cls.host_1 = cls.uc.add_host(provider=provider, fqdn="host_1", cluster=cls.cluster)
        cls.host_2 = cls.uc.add_host(provider=provider, fqdn="host_2", cluster=cls.cluster)
        cls.host_3 = cls.uc.add_host(provider=provider, fqdn="host_3", cluster=cls.cluster)
        cls.foreign_host = cls.uc.add_host(provider=provider, fqdn="foreign_host", cluster=second_cluster)

    def test_host_not_in_cluster_fail(self):
        service_no_requires = self.uc.add_services_to_cluster(names=["service_no_requires"], cluster=self.cluster)[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_not_in_cluster.pk, "componentId": component_1.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_NOT_FOUND",
                "level": "error",
                "desc": f'Host(s) "{self.host_not_in_cluster.pk}" '
                f'do not belong to cluster "{self.cluster.display_name}"',
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_foreign_host_fail(self):
        service_no_requires = self.uc.add_services_to_cluster(names=["service_no_requires"], cluster=self.cluster)[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.foreign_host.pk, "componentId": component_1.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_NOT_FOUND",
                "level": "error",
                "desc": (f'Host(s) "{self.foreign_host.pk}" do not belong to cluster "{self.cluster.display_name}"'),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_non_existent_host_fail(self):
        service_no_requires = self.uc.add_services_to_cluster(names=["service_no_requires"], cluster=self.cluster)[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )
        non_existent_host_pk = self.get_non_existent_pk(model=Host)

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": non_existent_host_pk, "componentId": component_1.pk},
                {"hostId": non_existent_host_pk + 1, "componentId": component_1.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_NOT_FOUND",
                "level": "error",
                "desc": f'Host(s) "{non_existent_host_pk}", "{non_existent_host_pk + 1}" '
                f'do not belong to cluster "{self.cluster.display_name}"',
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_non_existent_component_fail(self):
        service_no_requires = self.uc.add_services_to_cluster(names=["service_no_requires"], cluster=self.cluster)[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )
        non_existent_component_pk = self.get_non_existent_pk(model=Component)

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_1.pk, "componentId": non_existent_component_pk},
                {"hostId": self.host_1.pk, "componentId": non_existent_component_pk + 1},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_NOT_FOUND",
                "level": "error",
                "desc": f'Component(s) "{non_existent_component_pk}", "{non_existent_component_pk + 1}" '
                f'do not belong to cluster "{self.cluster.display_name}"',
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_no_required_service_fail(self):
        service_requires_service = self.uc.add_services_to_cluster(
            names=["service_requires_service"], cluster=self.cluster
        )[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_requires_service, cluster=self.cluster
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "level": "error",
                "desc": f'No required service "service_required" for service "{service_requires_service.display_name}"',
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_required_service_success(self):
        service_requires_service = self.uc.add_services_to_cluster(
            names=["service_requires_service"], cluster=self.cluster
        )[0]
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_requires_service, cluster=self.cluster
        )
        # required service must be added (not exactly mapped) on mapping save
        self.uc.add_services_to_cluster(names=["service_required"], cluster=self.cluster)[0]

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": self.host_1.pk, "componentId": component_1.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 1)

    def test_no_required_component_fail(self):
        service_requires_component = self.uc.add_services_to_cluster(
            names=["service_requires_component"], cluster=self.cluster
        )[0]
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )
        service_with_component_required = self.uc.add_services_to_cluster(
            names=["service_with_component_required"], cluster=self.cluster
        )[0]
        not_required_component = Component.objects.get(
            prototype__name="not_required_component",
            service=service_with_component_required,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_1.pk, "componentId": not_required_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": (
                    'No required component "required_component" of service "service_with_component_required" '
                    f'for service "{service_requires_component.display_name}"'
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_no_required_component_but_unrequired_component_present_fail(self):
        service_requires_component = self.uc.add_services_to_cluster(
            names=["service_requires_component"], cluster=self.cluster
        )[0]
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )

        service_with_component_required = self.uc.add_services_to_cluster(
            names=["service_with_component_required"], cluster=self.cluster
        )[0]
        not_required_component = Component.objects.get(
            prototype__name="not_required_component",
            service=service_with_component_required,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_1.pk, "componentId": not_required_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": (
                    'No required component "required_component" of service "service_with_component_required" '
                    f'for service "{service_requires_component.display_name}"'
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_required_component_success(self):
        service_requires_component = self.uc.add_services_to_cluster(
            names=["service_requires_component"], cluster=self.cluster
        )[0]
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )

        service_with_component_required = self.uc.add_services_to_cluster(
            names=["service_with_component_required"], cluster=self.cluster
        )[0]
        required_component = Component.objects.get(
            prototype__name="required_component",
            service=service_with_component_required,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_1.pk, "componentId": required_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 2)

    def test_no_bound_fail(self):
        service_with_bound_component = self.uc.add_services_to_cluster(
            names=["service_with_bound_component"], cluster=self.cluster
        )[0]
        bound_component = Component.objects.get(
            prototype__name="bound_component",
            service=service_with_bound_component,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": bound_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        data = response.json()
        self.assertEqual(data["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertIn("Component `bound_to` restriction violated.", data["desc"])
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_bound_on_different_host_fail(self):
        service_with_bound_component = self.uc.add_services_to_cluster(
            names=["service_with_bound_component"], cluster=self.cluster
        )[0]
        bound_component = Component.objects.get(
            prototype__name="bound_component",
            service=service_with_bound_component,
            cluster=self.cluster,
        )

        bound_target_service = self.uc.add_services_to_cluster(names=["bound_target_service"], cluster=self.cluster)[0]
        bound_target_component = Component.objects.get(
            prototype__name="bound_target_component",
            service=bound_target_service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": bound_component.pk},
                {"hostId": self.host_2.pk, "componentId": bound_target_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        data = response.json()
        self.assertEqual(data["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertIn("Component `bound_to` restriction violated.", data["desc"])
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_bound_success(self):
        service_with_bound_component = self.uc.add_services_to_cluster(
            names=["service_with_bound_component"], cluster=self.cluster
        )[0]
        bound_component = Component.objects.get(
            prototype__name="bound_component",
            service=service_with_bound_component,
            cluster=self.cluster,
        )

        bound_target_service = self.uc.add_services_to_cluster(names=["bound_target_service"], cluster=self.cluster)[0]
        bound_target_component = Component.objects.get(
            prototype__name="bound_target_component",
            service=bound_target_service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": bound_component.pk},
                {"hostId": self.host_1.pk, "componentId": bound_target_component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 2)

    def test_one_constraint_zero_in_hc_fail(self):
        service = self.uc.add_services_to_cluster(
            names=["service_with_one_component_constraint"], cluster=self.cluster
        )[0]
        component = Component.objects.get(
            prototype__name="one",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(data=[])

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": (
                    f'Component "{component.display_name}" of service "{component.service.name}" '
                    f"has unsatisfied constraint: {component.prototype.constraint}"
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_constraint_two_in_hc_fail(self):
        service = self.uc.add_services_to_cluster(
            names=["service_with_one_component_constraint"], cluster=self.cluster
        )[0]
        component = Component.objects.get(
            prototype__name="one",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": (
                    f'Component "{component.display_name}" of service "{component.service.name}" '
                    f"has unsatisfied constraint: {component.prototype.constraint}"
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_constraint_success(self):
        service = self.uc.add_services_to_cluster(
            names=["service_with_one_component_constraint"], cluster=self.cluster
        )[0]
        component = Component.objects.get(
            prototype__name="one",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": self.host_1.pk, "componentId": component.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 1)

    def test_zero_one_constraint_two_in_hc_fail(self):
        service = self.uc.add_services_to_cluster(
            names=["service_with_zero_one_component_constraint"], cluster=self.cluster
        )[0]
        component = Component.objects.get(
            prototype__name="zero_one",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": (
                    f'Component "{component.display_name}" of service "{component.service.name}" '
                    f"has unsatisfied constraint: {component.prototype.constraint}"
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_zero_one_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_zero_one_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="zero_one",
            service=service,
            cluster=self.cluster,
        )

        for data in ([], [{"hostId": self.host_1.pk, "componentId": component.pk}]):
            with self.subTest(f"[0,1] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_one_two_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_two_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_two",
            service=service,
            cluster=self.cluster,
        )

        err_msg = (
            f'Component "{component.display_name}" of service "{component.service.name}" '
            f"has unsatisfied constraint: {component.prototype.constraint}"
        )
        for data in (
            [],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[1,2] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertDictEqual(
                    response.json(),
                    {
                        "code": "COMPONENT_CONSTRAINT_ERROR",
                        "level": "error",
                        "desc": err_msg,
                    },
                )
                self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_two_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_two_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_two",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[1,2] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_one_odd_first_variant_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_odd_component_constraint_1"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_odd_first_variant",
            service=service,
            cluster=self.cluster,
        )

        err_msg = (
            f'Component "{component.display_name}" of service "{component.service.name}" '
            f"has unsatisfied constraint: {component.prototype.constraint}"
        )
        for data in (
            [],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[1,odd] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertDictEqual(
                    response.json(),
                    {
                        "code": "COMPONENT_CONSTRAINT_ERROR",
                        "level": "error",
                        "desc": err_msg,
                    },
                )
                self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_odd_first_variant_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_odd_component_constraint_1"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_odd_first_variant",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[1,odd] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_one_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one",
            service=service,
            cluster=self.cluster,
        )

        err_msg = (
            f'Component "{component.display_name}" of service "{component.service.name}" '
            f"has unsatisfied constraint: {component.prototype.constraint}"
        )
        for data in (
            [],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[odd] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertDictEqual(
                    response.json(),
                    {
                        "code": "COMPONENT_CONSTRAINT_ERROR",
                        "level": "error",
                        "desc": err_msg,
                    },
                )
                self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_odd_second_variant_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_odd_component_constraint_2"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_odd_second_variant",
            service=service,
            cluster=self.cluster,
        )
        err_msg = (
            f'Component "{component.display_name}" of service "{component.service.name}" '
            f"has unsatisfied constraint: {component.prototype.constraint}"
        )
        for data in (
            [],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[odd] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertDictEqual(
                    response.json(),
                    {
                        "code": "COMPONENT_CONSTRAINT_ERROR",
                        "level": "error",
                        "desc": err_msg,
                    },
                )
                self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_odd_second_variant_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_odd_component_constraint_2"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_odd_second_variant",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[odd] constraint, data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_zero_odd_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_zero_odd_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="zero_odd",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": f'Component "{component.display_name}" of service "{component.service.name}" '
                f"has unsatisfied constraint: {component.prototype.constraint}",
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_zero_odd_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_zero_odd_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="zero_odd",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [],
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[0,odd], data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_zero_plus_constraint_success(self):
        service = self.add_services_to_cluster(service_names=["bound_target_service"], cluster=self.cluster).get()
        component = Component.objects.get(
            prototype__name="bound_target_component",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [],
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[0,+], data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_one_plus_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_plus_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_plus",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(data=[])

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": f'Component "{component.display_name}" of service "{component.service.name}" '
                f"has unsatisfied constraint: {component.prototype.constraint}",
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_one_plus_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_one_plus_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="one_plus",
            service=service,
            cluster=self.cluster,
        )

        for data in (
            [{"hostId": self.host_1.pk, "componentId": component.pk}],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
            [
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
                {"hostId": self.host_3.pk, "componentId": component.pk},
            ],
        ):
            with self.subTest(f"[1,+], data: {data}"):
                response = self.client.v2[self.cluster, "mapping"].post(data=data)

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(HostComponent.objects.count(), len(data))

    def test_plus_constraint_fail(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_plus_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="plus",
            service=service,
            cluster=self.cluster,
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component.pk},
                {"hostId": self.host_2.pk, "componentId": component.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": f'Component "{component.display_name}" of service "{component.service.name}" '
                f"has unsatisfied constraint: {component.prototype.constraint}",
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_plus_constraint_success(self):
        service = self.add_services_to_cluster(
            service_names=["service_with_plus_component_constraint"], cluster=self.cluster
        ).get()
        component = Component.objects.get(
            prototype__name="plus",
            service=service,
            cluster=self.cluster,
        )

        data = [{"hostId": host.pk, "componentId": component.pk} for host in self.cluster.host_set.all()]
        response = self.client.v2[self.cluster, "mapping"].post(data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), len(data))

    def test_no_required_service_not_in_hc_fail(self):
        """check that cluster has not any unsatisfied service/component requirements not present in hc"""

        service_requires_service = self.add_services_to_cluster(
            service_names=["service_requires_service"], cluster=self.cluster
        ).get()

        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": self.host_1.pk, "componentId": component_1.pk}],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "level": "error",
                "desc": (
                    f'No required service "service_required" for service ' f'"{service_requires_service.display_name}"'
                ),
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_host_in_mm_fail(self):
        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_no_requires, cluster=self.cluster
        )

        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.host_1.pk, "componentId": component_1.pk},
                {"hostId": self.host_2.pk, "componentId": component_1.pk},
            ],
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "INVALID_HC_HOST_IN_MM",
                "level": "error",
                "desc": "You can't save hc with hosts in maintenance mode",
            },
        )
        self.assertEqual(HostComponent.objects.count(), 0)


class TestBoundTo(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        bundles_dir = cls.test_bundles_dir / "adcm_7894"
        cls.old_bundle = cls.uc.upload_bundle(bundles_dir / "old")
        cls.new_bundle = cls.uc.upload_bundle(bundles_dir / "new")

        provider_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "provider")
        provider = cls.uc.add_provider(bundle=provider_bundle)
        cls.host_1 = cls.uc.add_host(provider=provider, name="host-1")
        cls.host_2 = cls.uc.add_host(provider=provider, name="host-2")

    def prepare_cluster_with_two_components(self, bundle: Bundle) -> tuple[Cluster, Component, Component]:
        cluster = self.uc.add_cluster(bundle=bundle)
        self.uc.add_services_to_cluster(["service_1", "service_with_bound_to_component"], cluster=cluster)
        self.uc.add_host_to_cluster(host=self.host_1, cluster=cluster)
        self.uc.add_host_to_cluster(host=self.host_2, cluster=cluster)
        component = Component.objects.get(service__prototype__name="service_1", prototype__name="component_1")
        dependent_component = Component.objects.get(
            service__prototype__name="service_with_bound_to_component", prototype__name="will_have_bound_to"
        )
        return cluster, component, dependent_component

    def test_concern_appear_after_upgrade_success(self) -> None:
        upgrade = Upgrade.objects.get(name="upgrade")
        cluster_old, component, dependent_component = self.prepare_cluster_with_two_components(self.old_bundle)
        self.uc.set_hostcomponent(
            cluster=cluster_old,
            entries=((self.host_1, component), (self.host_2, component), (self.host_2, dependent_component)),
        )
        self.assertFalse(ConcernItem.objects.filter(cause=ConcernCause.HOSTCOMPONENT).exists())

        response = self.client.v2[cluster_old, "upgrades", upgrade, "run"].post()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        concern = ConcernItem.objects.filter(cause=ConcernCause.HOSTCOMPONENT).first()
        self.assertIsNotNone(concern)
        cluster_old.refresh_from_db()
        self.assertEqual(concern.owner, cluster_old)

    def test_save_mapping_with_unsatisfied_bound_to_fail(self) -> None:
        cluster_new, component, dependent_component = self.prepare_cluster_with_two_components(self.new_bundle)
        mapping_to_set = [
            {"hostId": host.id, "componentId": component.id}
            for host, component in (
                (self.host_1, component),
                (self.host_2, component),
                (self.host_2, dependent_component),
            )
        ]

        response = self.client.v2[cluster_new, "mapping"].post(data=mapping_to_set)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        data = response.json()
        self.assertEqual(data["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertIn("Component `bound_to` restriction violated.", data["desc"])


class ConfigHostGroupRelatedTests(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)

        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host_1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host_2", cluster=cls.cluster_1)

        cls.service_1 = Service.objects.get(prototype__name="service_1", cluster=cls.cluster_1)
        cls.component_1_from_s1 = Component.objects.get(prototype__name="component_1", service=cls.service_1)
        cls.component_2_from_s1 = Component.objects.get(prototype__name="component_2", service=cls.service_1)

    def _prepare_config_host_group_via_api(
        self, obj: Cluster | Service | Component, hosts: list[Host], name: str, description: str = ""
    ) -> ConfigHostGroup:
        response = self.client.v2[obj, "config-groups"].post(data={"name": name, "description": description})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group = ConfigHostGroup.objects.get(pk=response.json()["id"])

        for host in hosts:
            response = self.client.v2[host_group, "hosts"].post(data={"hostId": host.pk})
            self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group.refresh_from_db()
        self.assertEqual(host_group.hosts.count(), len(hosts))

        return host_group

    def test_host_removed_from_component_config_host_group_on_mapping_change(self):
        mapping_data = [{"hostId": self.host_1.pk, "componentId": self.component_1_from_s1.pk}]

        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group = self._prepare_config_host_group_via_api(
            obj=self.component_1_from_s1, hosts=[self.host_1], name="component config group"
        )

        mapping_data[0].update({"componentId": self.component_2_from_s1.pk})
        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group.refresh_from_db()
        self.assertEqual(host_group.hosts.count(), 0)

    def test_host_not_removed_from_component_config_host_group_on_mapping_remain(self):
        endpoint = self.client.v2[self.cluster_1, "mapping"]
        mapping_data = [{"hostId": self.host_1.pk, "componentId": self.component_1_from_s1.pk}]

        response = endpoint.post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group = self._prepare_config_host_group_via_api(
            obj=self.component_1_from_s1, hosts=[self.host_1], name="component config group"
        )

        mapping_data.append({"hostId": self.host_2.pk, "componentId": self.component_2_from_s1.pk})
        response = endpoint.post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group.refresh_from_db()
        self.assertSetEqual(set(host_group.hosts.values_list("pk", flat=True)), {self.host_1.pk})

    def test_host_not_removed_from_service_config_host_group_on_mapping_remain(self):
        mapping_data = [{"hostId": self.host_1.pk, "componentId": self.component_1_from_s1.pk}]

        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group = self._prepare_config_host_group_via_api(
            obj=self.service_1, hosts=[self.host_1], name="service config group"
        )

        mapping_data.insert(0, {"hostId": self.host_2.pk, "componentId": self.component_2_from_s1.pk})
        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group.refresh_from_db()
        self.assertSetEqual(set(host_group.hosts.values_list("pk", flat=True)), {self.host_1.pk})

    def test_host_not_removed_from_cluster_config_host_group_on_mapping_change(self):
        mapping_data = [{"hostId": self.host_1.pk, "componentId": self.component_1_from_s1.pk}]

        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group = self._prepare_config_host_group_via_api(
            obj=self.cluster_1, hosts=[self.host_1], name="cluster config group"
        )

        mapping_data[0].update({"componentId": self.component_2_from_s1.pk})
        response = self.client.v2[self.cluster_1, "mapping"].post(data=mapping_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_group.refresh_from_db()
        self.assertSetEqual(set(host_group.hosts.values_list("pk", flat=True)), {self.host_1.pk})


class TestMappingNew(ADCMDjangoAPISuite, APIV2Mixin, TestUtilsMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_one")
        cls.cluster_1 = cls.uc.add_cluster(bundle=cluster_bundle, name="Test cluster for mapping")
        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)[0]
        cls.component_1 = Component.objects.get(prototype__name="component_1", service=cls.service_1)
        # existence check, needed to set component's MM = ON without affecting service's MM
        Component.objects.get(prototype__name="component_2", service=cls.service_1)

        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")
        provider = cls.uc.add_provider(bundle=provider_bundle, name="provider")
        cls.host_1 = cls.uc.add_host(provider=provider, name="host-1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=provider, name="host-2", cluster=cls.cluster_1)

    def test_add_remove_simple_success(self):
        self.check_mm_is_on_only_for(obj=None, cluster_id=self.cluster_1.id)
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_1), (self.host_2, self.component_1))
        )
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_add_host_in_mm_fail(self):
        self.service_1.refresh_from_db()
        self.assertEqual(self.service_1.state, "created")
        self.set_maintenance_mode(obj=self.host_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.host_1, cluster_id=self.cluster_1.id)
        with self.assertRaises(AssertionError, msg="Mapping creation failed: 409"):
            self.create_mapping(cluster=self.cluster_1, entries=((self.host_1, self.component_1),))

    def test_adcm_7530_add_host_not_in_mm_to_service_not_in_created_state_success(self):
        self.service_1.state = "not created"
        self.service_1.save(update_fields=["state"])

        self.check_mm_is_on_only_for(obj=None, cluster_id=self.cluster_1.id)
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_add_host_in_mm_to_service_not_in_created_state_fail(self):
        self.set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)
        self.service_1.state = "not created"
        self.service_1.save(update_fields=["state"])

        self.check_mm_is_on_only_for(obj=self.host_2, cluster_id=self.cluster_1.id)
        with self.assertRaises(AssertionError, msg="Mapping creation failed: 409"):
            self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_remove_host_in_mm_success(self):
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_1), (self.host_2, self.component_1))
        )
        self.set_maintenance_mode(obj=self.host_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.host_1, cluster_id=self.cluster_1.id)
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_remove_host_not_in_mm_from_service_not_in_created_state_success(self):
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_1), (self.host_2, self.component_1))
        )
        self.service_1.state = "not created"
        self.service_1.save(update_fields=["state"])

        self.check_mm_is_on_only_for(obj=None, cluster_id=self.cluster_1.id)
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_remove_host_in_mm_from_service_not_in_created_state_success(self):
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_1), (self.host_2, self.component_1))
        )
        self.set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)
        self.service_1.state = "not created"
        self.service_1.save(update_fields=["state"])

        self.check_mm_is_on_only_for(obj=self.host_2, cluster_id=self.cluster_1.id)
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))

    def test_adcm_7530_add_remove_from_component_in_mm_success(self):
        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.component_1, cluster_id=self.cluster_1.id)
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_1), (self.host_2, self.component_1))
        )
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_2, self.component_1),))


class TestHC(ADCMDjangoAPISuite):
    # moved from cm.tests.test_hc
    def test_adcm_4929_run_same_hc_success(self) -> None:
        # Since it was moved from CM, need to pass it,
        # moving it is risky, copying not solving any problems.
        # Sorry if you've got here after deleting it :3
        bundles_dir = Path(__file__).parent.parent.parent / "cm" / "tests" / "bundles"
        bundle = self.uc.upload_bundle(bundles_dir / "cluster_1")
        cluster = self.add_cluster(bundle=bundle, name="Cool")
        service_1 = self.add_services_to_cluster(["service_one_component"], cluster=cluster).get()
        service_2 = self.add_services_to_cluster(["service_two_components"], cluster=cluster).get()
        service_with_action = self.add_services_to_cluster(["with_hc_acl_actions"], cluster=cluster).get()

        host_1 = self.add_host(provider=self.provider, fqdn="host-1")
        host_2 = self.add_host(provider=self.provider, fqdn="host-2")

        self.add_host_to_cluster(cluster, host_1)
        self.add_host_to_cluster(cluster, host_2)

        component_1_1 = Component.objects.get(service=service_1, prototype__name="component_1")
        component_2_1 = Component.objects.get(service=service_2, prototype__name="component_1")
        component_2_2 = Component.objects.get(service=service_2, prototype__name="component_2")
        hc = self.set_hostcomponent(
            cluster=cluster,
            entries=(
                (host_1, component_1_1),
                (host_1, component_2_1),
                (host_1, component_2_2),
                (host_2, component_2_1),
                (host_2, component_2_2),
            ),
        )
        action = Action.objects.get(prototype=service_with_action.prototype, name="with_hc")

        response = self.client.v2[service_with_action, "actions", action.pk, "run"].post(
            data={
                "hostComponentMap": [{"hostId": entry.host_id, "componentId": entry.component_id} for entry in hc],
            },
        )

        # expectations changed due to existing behavior in bundles
        self.assertEqual(response.status_code, HTTP_200_OK)
