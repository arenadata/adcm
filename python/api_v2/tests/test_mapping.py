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

from cm.models import (
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConfigHostGroup,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    Service,
    Upgrade,
)
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestMapping(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_B")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_A")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_C")
        self.add_host_to_cluster(cluster=self.cluster_2, host=self.host_3)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = Component.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_2 = Component.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )
        self.component_3 = Component.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_3"
        )

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, self.component_1)])

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_list_mapping_success(self):
        response = self.client.v2[self.cluster_1, "mapping"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertDictEqual(response.json()[0], {"componentId": 1, "hostId": 1, "id": 1})

    def test_create_mapping_success(self):
        host_4 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_4")
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
        host_4 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_4", cluster=self.cluster_1
        )

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
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_requires_component")
        cluster = self.add_cluster(bundle=bundle, name="cluster_requires")
        self.add_services_to_cluster(service_names=["hbase", "zookeeper", "hdfs"], cluster=cluster)

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


class TestMappingConstraints(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "hc_mapping_constraints")
        provider_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "provider")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cluster_with_hc_requirements")
        second_cluster = self.add_cluster(bundle=cluster_bundle, name="second_cluster")

        provider = self.add_provider(bundle=provider_bundle, name="provider")

        self.host_not_in_cluster = self.add_host(bundle=provider_bundle, provider=provider, fqdn="host_not_in_cluster")
        self.host_1 = self.add_host(bundle=provider_bundle, provider=provider, fqdn="host_1", cluster=self.cluster)
        self.host_2 = self.add_host(bundle=provider_bundle, provider=provider, fqdn="host_2", cluster=self.cluster)
        self.host_3 = self.add_host(bundle=provider_bundle, provider=provider, fqdn="host_3", cluster=self.cluster)
        self.foreign_host = self.add_host(
            bundle=provider_bundle, provider=provider, fqdn="foreign_host", cluster=second_cluster
        )

    def test_host_not_in_cluster_fail(self):
        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
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
        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
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
        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
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
        service_no_requires = self.add_services_to_cluster(
            service_names=["service_no_requires"], cluster=self.cluster
        ).get()
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
        service_requires_service = self.add_services_to_cluster(
            service_names=["service_requires_service"], cluster=self.cluster
        ).get()
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
        service_requires_service = self.add_services_to_cluster(
            service_names=["service_requires_service"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1", service=service_requires_service, cluster=self.cluster
        )
        # required service must be added (not exactly mapped) on mapping save
        self.add_services_to_cluster(service_names=["service_required"], cluster=self.cluster).get()

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[{"hostId": self.host_1.pk, "componentId": component_1.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 1)

    def test_no_required_component_fail(self):
        service_requires_component = self.add_services_to_cluster(
            service_names=["service_requires_component"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )
        service_with_component_required = self.add_services_to_cluster(
            service_names=["service_with_component_required"], cluster=self.cluster
        ).get()
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
        service_requires_component = self.add_services_to_cluster(
            service_names=["service_requires_component"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )

        service_with_component_required = self.add_services_to_cluster(
            service_names=["service_with_component_required"], cluster=self.cluster
        ).get()
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
        service_requires_component = self.add_services_to_cluster(
            service_names=["service_requires_component"], cluster=self.cluster
        ).get()
        component_1 = Component.objects.get(
            prototype__name="component_1",
            service=service_requires_component,
            cluster=self.cluster,
        )

        service_with_component_required = self.add_services_to_cluster(
            service_names=["service_with_component_required"], cluster=self.cluster
        ).get()
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
        service_with_bound_component = self.add_services_to_cluster(
            service_names=["service_with_bound_component"], cluster=self.cluster
        ).get()
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
        service_with_bound_component = self.add_services_to_cluster(
            service_names=["service_with_bound_component"], cluster=self.cluster
        ).get()
        bound_component = Component.objects.get(
            prototype__name="bound_component",
            service=service_with_bound_component,
            cluster=self.cluster,
        )

        bound_target_service = self.add_services_to_cluster(
            service_names=["bound_target_service"], cluster=self.cluster
        ).get()
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
        service_with_bound_component = self.add_services_to_cluster(
            service_names=["service_with_bound_component"], cluster=self.cluster
        ).get()
        bound_component = Component.objects.get(
            prototype__name="bound_component",
            service=service_with_bound_component,
            cluster=self.cluster,
        )

        bound_target_service = self.add_services_to_cluster(
            service_names=["bound_target_service"], cluster=self.cluster
        ).get()
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
        service = self.add_services_to_cluster(
            service_names=["service_with_one_component_constraint"], cluster=self.cluster
        ).get()
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
        service = self.add_services_to_cluster(
            service_names=["service_with_one_component_constraint"], cluster=self.cluster
        ).get()
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
        service = self.add_services_to_cluster(
            service_names=["service_with_one_component_constraint"], cluster=self.cluster
        ).get()
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
        service = self.add_services_to_cluster(
            service_names=["service_with_zero_one_component_constraint"], cluster=self.cluster
        ).get()
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


class TestBoundTo(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.old_bundle = Bundle.objects.get(name="cluster_one", version="1.0")
        self.new_bundle = self.add_bundle(self.test_bundles_dir / "cluster_one_upgrade")
        Prototype.objects.filter(license="unaccepted").update(license="accepted")

    def test_concern_appear_after_upgrade_success(self) -> None:
        cluster_old = self.add_cluster(bundle=self.old_bundle, name="Created Old")

        service = self.add_services_to_cluster(["service_1"], cluster=cluster_old).get()
        component = service.components.get(prototype__name="component_1")
        service_with_dependency = self.add_services_to_cluster(["service_with_bound_to"], cluster=cluster_old).get()
        dependent_component = service_with_dependency.components.get(prototype__name="will_have_bound_to")

        host_1 = self.add_host(provider=self.provider, fqdn="h1", cluster=cluster_old)
        host_2 = self.add_host(provider=self.provider, fqdn="h2", cluster=cluster_old)

        self.set_hostcomponent(
            cluster=cluster_old, entries=((host_1, component), (host_2, component), (host_2, dependent_component))
        )

        self.assertFalse(ConcernItem.objects.filter(cause=ConcernCause.HOSTCOMPONENT).exists())

        upgrade = Upgrade.objects.get(name="upgrade")

        response = self.client.v2[cluster_old, "upgrades", upgrade, "run"].post()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        cluster_old.refresh_from_db()

        concern = ConcernItem.objects.filter(cause=ConcernCause.HOSTCOMPONENT).first()

        self.assertIsNotNone(concern)
        self.assertEqual(concern.owner, cluster_old)

    def test_save_mapping_with_unsatisfied_bound_to_fail(self) -> None:
        cluster_new = self.add_cluster(bundle=self.new_bundle, name="Created New")

        service = self.add_services_to_cluster(["service_1"], cluster=cluster_new).get()
        component = service.components.get(prototype__name="component_1")
        service_with_dependency = self.add_services_to_cluster(["service_with_bound_to"], cluster=cluster_new).get()
        dependent_component = service_with_dependency.components.get(prototype__name="will_have_bound_to")

        host_1 = self.add_host(provider=self.provider, fqdn="h1", cluster=cluster_new)
        host_2 = self.add_host(provider=self.provider, fqdn="h2", cluster=cluster_new)

        response = self.client.v2[cluster_new, "mapping"].post(
            data=[
                {"hostId": host.id, "componentId": component.id}
                for host, component in ((host_1, component), (host_2, component), (host_2, dependent_component))
            ]
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        data = response.json()
        self.assertEqual(data["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertIn("Component `bound_to` restriction violated.", data["desc"])


class ConfigHostGroupRelatedTests(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)

        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

        self.service_1 = Service.objects.get(prototype__name="service_1", cluster=self.cluster_1)
        self.component_1_from_s1 = Component.objects.get(prototype__name="component_1", service=self.service_1)
        self.component_2_from_s1 = Component.objects.get(prototype__name="component_2", service=self.service_1)

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
