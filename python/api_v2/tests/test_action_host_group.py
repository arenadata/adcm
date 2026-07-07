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

from contextlib import contextmanager, nullcontext
from functools import partial
from itertools import chain
from operator import itemgetter

from cm.converters import model_to_core_type, orm_object_to_core_type
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService
from cm.models import Action, ActionHostGroup, Cluster, Component, ConcernItem, Host, Service, TaskLog
from rbac.models import Role
from rbac.services.group import create
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuite
from unittest_parametrize import param, parametrize

ACTION_HOST_GROUPS = "action-host-groups"


class TestActionHostGroup(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_action_host_group")

        for i in range(3):
            cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name=f"Cluster {i}")
            cls.service, *_ = cls.uc.add_services_to_cluster(["example"], cluster=cls.cluster)
            cls.component = cls.service.components.first()

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Provider")
        cls.hosts = [cls.uc.add_host(provider=cls.provider, fqdn=f"host-{i}", cluster=cls.cluster) for i in range(3)]

        non_main_cluster = Cluster.objects.exclude(id=cls.cluster.pk).first()
        non_main_service = Service.objects.exclude(id=cls.service.pk).first()
        non_main_component = Component.objects.exclude(id=cls.component.pk).first()

        cls.cluster_ahg_1 = cls.uc.create_action_host_group(name="init", owner=non_main_cluster)
        cls.service_ahg_1 = cls.uc.create_action_host_group(name="init", owner=non_main_service)
        cls.component_ahg_1 = cls.uc.create_action_host_group(name="init", owner=non_main_component)

        cls.cluster_ahg_2 = cls.uc.create_action_host_group(name="second", owner=non_main_cluster)
        cls.service_ahg_2 = cls.uc.create_action_host_group(name="second", owner=non_main_service)
        cls.component_ahg_2 = cls.uc.create_action_host_group(name="second", owner=non_main_component)

    def assert_fields_in_ahg(self, group_id: int, expected: dict) -> None:
        actual = ActionHostGroup.objects.values(*expected.keys()).get(id=group_id)
        self.assertEqual(actual, expected)

    def test_create_group_success(self) -> None:
        group_counter = ActionHostGroup.objects.count()

        for target in (self.cluster, self.service, self.component):
            type_ = model_to_core_type(target.__class__)
            group_counter += 1

            data = {"name": f"group for {type_.value}", "description": "simple group"}

            response = self.client.v2[target, ACTION_HOST_GROUPS].post(data=data)

            with self.subTest(f"[{type_.name}] CREATED"):
                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(ActionHostGroup.objects.count(), group_counter)
                created_group = ActionHostGroup.objects.filter(
                    object_id=target.id, object_type=target.content_type, name=data["name"]
                ).first()
                self.assertIsNotNone(created_group)
                self.assertEqual(response.json(), {"id": created_group.id, **data, "hosts": []})

            with self.subTest(f"[{type_.name}] AUDITED"):
                self.check_last_audit_record(
                    operation_name=f"{data['name']} action host group created",
                    operation_type="create",
                    operation_result="success",
                    **self.prepare_audit_object_arguments(expected_object=target),
                )

        with self.subTest("[SERVICE] Without Description"):
            another_name = "whoah"
            response = self.client.v2[self.service, ACTION_HOST_GROUPS].post(data={"name": another_name})

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            data = response.json()
            self.assertEqual(data["name"], another_name)
            self.assertEqual(data["description"], "")

    def test_create_multiple_groups(self) -> None:
        with self.subTest("[COMPONENT] Same Object + Different Names SUCCESS"):
            endpoint = self.client.v2[self.component, ACTION_HOST_GROUPS]
            response = endpoint.post(data={"name": "best-1", "description": ""})
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            response = endpoint.post(data={"name": "best-2", "description": ""})
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            groups = sorted(
                ActionHostGroup.objects.values_list("name", flat=True).filter(
                    object_id=self.component.id, object_type=self.component.content_type
                )
            )
            self.assertListEqual(groups, ["best-1", "best-2"])

        with self.subTest("[SERVICE] Different Objects + Same Name SUCCESS"):
            second_service = Service.objects.exclude(id=self.service.id).first()
            data = {"name": "cool", "description": ""}

            response = self.client.v2[self.service, ACTION_HOST_GROUPS].post(data=data)
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            response = self.client.v2[second_service, ACTION_HOST_GROUPS].post(data=data)
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            groups = sorted(
                ActionHostGroup.objects.values_list("object_id", flat=True).filter(
                    name=data["name"], object_type=Service.class_content_type
                )
            )
            self.assertListEqual(groups, sorted((self.service.id, second_service.id)))

        with self.subTest("[SERVICE] Same Object + Same Name FAIL"):
            name = "sgroup"
            response = self.client.v2[self.service, ACTION_HOST_GROUPS].post(data={"name": name, "description": "cool"})
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response = self.client.v2[self.service, ACTION_HOST_GROUPS].post(data={"name": name, "description": "best"})

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "CREATE_CONFLICT")
            self.assertEqual(ActionHostGroup.objects.filter(name=name).count(), 1)

    @parametrize(
        ("owner_var_name", "payload", "expected"),
        [
            param(owner, payload, expected, id=f"{owner}_{data_name}")
            for owner in ("cluster", "service", "component")
            for data_name, payload, expected in (
                ("name_only", {"name": "changed"}, {"name": "changed", "description": ""}),
                ("description_only", {"description": "changed"}, {"name": "init", "description": "changed"}),
                (
                    "name_and_description_new",
                    {"name": "changed", "description": "desc"},
                    {"name": "changed", "description": "desc"},
                ),
                ("name_and_description_same", {"name": "init", "description": ""}, {"name": "init", "description": ""}),
                ("nothing", {}, {"name": "init", "description": ""}),
            )
        ],
    )
    def test_update_success(self, owner_var_name: str, payload: dict, expected: dict) -> None:
        group = getattr(self, f"{owner_var_name}_ahg_1")

        response = self.client.v2[group].patch(data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item in response.json().items() for item in expected.items()))
        self.assert_fields_in_ahg(group.pk, expected)
        self.check_last_audit_record(
            operation_name=f"{group.name} action host group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=group.object),
        )

    @parametrize("owner_var_name", ["cluster", "service", "component"])
    def test_update_to_taken_name_fail(self, owner_var_name: str) -> None:
        payload = {"name": "second"}
        expected = {"name": "init", "description": ""}
        group = getattr(self, f"{owner_var_name}_ahg_1")

        response = self.client.v2[group].patch(data=payload)

        self.assertEqual(response.status_code, 409)
        self.assertIn("already exists", response.json()["desc"])
        self.assert_fields_in_ahg(group.pk, expected)

    def test_delete_success(self) -> None:
        self.uc.set_hostcomponent(
            cluster=self.cluster, entries=((self.hosts[0], self.component), (self.hosts[1], self.component))
        )

        cluster_group = self.uc.create_action_host_group(name="Cluster Group", owner=self.cluster)
        self.uc.add_hosts_to_action_host_group(group_id=cluster_group.id, hosts=[self.hosts[0].id])
        service_group_1 = self.uc.create_action_host_group(name="Service Group", owner=self.service)
        self.uc.create_action_host_group(name="Service Group #2", owner=self.service)
        component_group = self.uc.create_action_host_group(name="Component Group", owner=self.component)
        self.uc.add_hosts_to_action_host_group(group_id=component_group.id, hosts=[self.hosts[0].id, self.hosts[1].id])

        for target, group_to_delete, groups_left_amount in (
            (self.cluster, cluster_group, 0),
            (self.service, service_group_1, 1),
            (self.component, component_group, 0),
        ):
            type_name = orm_object_to_core_type(target).name

            with self.subTest(f"[{type_name}] DELETE SUCCESS"):
                response = self.client.v2[group_to_delete].delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                self.assertEqual(
                    ActionHostGroup.objects.filter(object_id=target.id, object_type=target.content_type).count(),
                    groups_left_amount,
                )

            with self.subTest(f"[{type_name}] DELETE AUDITED"):
                self.check_last_audit_record(
                    operation_name=f"{group_to_delete.name} action host group deleted",
                    operation_type="delete",
                    operation_result="success",
                    **self.prepare_audit_object_arguments(expected_object=target),
                )

    def test_unlink_host_from_component_success(self) -> None:
        service_2, *_ = self.uc.add_services_to_cluster(["second"], cluster=self.cluster)

        component_2 = self.service.components.last()
        component_3 = service_2.components.last()
        self.hosts += [
            self.uc.add_host(provider=self.provider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(3, 6)
        ]

        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=(
                (self.hosts[0], self.component),
                (self.hosts[1], self.component),
                (self.hosts[3], component_2),
                (self.hosts[4], component_2),
                (self.hosts[5], component_2),
                (self.hosts[0], component_3),
                (self.hosts[1], component_3),
                (self.hosts[2], component_3),
            ),
        )

        component_group = self.uc.create_action_host_group(name="Component Group", owner=self.component)
        component_group_2 = self.uc.create_action_host_group(name="Component Group 2", owner=component_2)
        component_group_3 = self.uc.create_action_host_group(name="Component Group 3", owner=component_3)
        self.uc.add_hosts_to_action_host_group(group_id=component_group.id, hosts=[self.hosts[0].id, self.hosts[1].id])

        self.uc.add_hosts_to_action_host_group(
            group_id=component_group_2.id, hosts=[self.hosts[3].id, self.hosts[4].id, self.hosts[5].id]
        )

        self.uc.add_hosts_to_action_host_group(
            group_id=component_group_3.id, hosts=[self.hosts[0].id, self.hosts[1].id, self.hosts[2].id]
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.hosts[4].id, "componentId": component_2.pk},
                {"hostId": self.hosts[5].id, "componentId": component_2.pk},
                {"hostId": self.hosts[0].id, "componentId": component_3.pk},
                {"hostId": self.hosts[1].id, "componentId": component_3.pk},
                {"hostId": self.hosts[2].id, "componentId": component_3.pk},
            ]
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.assertEqual(
            ActionHostGroup.objects.filter(
                object_id__in=(self.component.id, component_2.id, component_3.id),
                object_type=self.component.content_type,
            ).count(),
            3,
        )
        self.assertEqual(
            component_group.hosts.count(),
            0,
        )

        self.assertEqual(
            component_group_2.hosts.count(),
            2,
        )

        self.assertEqual(
            component_group_3.hosts.count(),
            3,
        )

    def test_move_host_to_another_component_success(self) -> None:
        service_2, *_ = self.uc.add_services_to_cluster(["second"], cluster=self.cluster)
        component_1 = service_2.components.first()
        component_2 = service_2.components.last()

        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=(
                (self.hosts[0], self.component),
                (self.hosts[1], self.component),
                (self.hosts[2], self.component),
                (self.hosts[0], component_1),
                (self.hosts[1], component_1),
                (self.hosts[2], component_1),
                (self.hosts[0], component_2),
            ),
        )

        service_group = self.uc.create_action_host_group(name="Service Group", owner=self.service)
        service_group_2 = self.uc.create_action_host_group(name="Service Group 2", owner=service_2)

        component_group = self.uc.create_action_host_group(name="Component Group", owner=self.component)
        component_group_2 = self.uc.create_action_host_group(name="Component Group 2", owner=component_1)
        component_group_3 = self.uc.create_action_host_group(name="Component Group 3", owner=component_2)

        for group in [service_group, service_group_2, component_group, component_group_2]:
            self.uc.add_hosts_to_action_host_group(
                group_id=group.id, hosts=[self.hosts[0].id, self.hosts[1].id, self.hosts[2].id]
            )

        self.uc.add_hosts_to_action_host_group(group_id=component_group_3.id, hosts=[self.hosts[0].id])

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.hosts[2].id, "componentId": self.component.pk},
                {"hostId": self.hosts[1].id, "componentId": self.component.pk},
                {"hostId": self.hosts[2].id, "componentId": component_1.pk},
                {"hostId": self.hosts[0].id, "componentId": component_1.pk},
            ]
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        for group in [service_group, component_group]:
            self.assertListEqual(
                list(group.hosts.order_by("id")),
                [self.hosts[1], self.hosts[2]],
            )

        for group in [service_group_2, component_group_2]:
            self.assertListEqual(
                list(group.hosts.order_by("id")),
                [self.hosts[0], self.hosts[2]],
            )

        self.assertEqual(component_group_3.hosts.count(), 0)

    def test_unlink_hosts_from_correct_service_success(self) -> None:
        service_2, *_ = self.uc.add_services_to_cluster(["second"], cluster=self.cluster)
        component_2 = service_2.components.last()
        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=(
                (self.hosts[0], self.component),
                (self.hosts[1], self.component),
                (self.hosts[0], component_2),
                (self.hosts[1], component_2),
            ),
        )

        component_group = self.uc.create_action_host_group(name="Component Group", owner=self.component)
        component_group_2 = self.uc.create_action_host_group(name="Component Group 2", owner=component_2)

        self.uc.add_hosts_to_action_host_group(group_id=component_group.id, hosts=[self.hosts[0].id, self.hosts[1].id])

        self.uc.add_hosts_to_action_host_group(
            group_id=component_group_2.id, hosts=[self.hosts[0].id, self.hosts[1].id]
        )

        response = self.client.v2[self.cluster, "mapping"].post(
            data=[
                {"hostId": self.hosts[0].id, "componentId": self.component.pk},
                {"hostId": self.hosts[1].id, "componentId": component_2.pk},
            ]
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.assertListEqual(
            list(component_group.hosts.all()),
            [self.hosts[0]],
        )

        self.assertListEqual(
            list(component_group_2.hosts.all()),
            [self.hosts[1]],
        )

    def test_unlink_host_from_cluster_service_and_component_success(self) -> None:
        self.uc.set_hostcomponent(
            cluster=self.cluster, entries=((self.hosts[0], self.component), (self.hosts[1], self.component))
        )

        cluster_group = self.uc.create_action_host_group(name="Cluster Group", owner=self.cluster)
        self.uc.add_hosts_to_action_host_group(group_id=cluster_group.id, hosts=[self.hosts[0].id])
        service_group_1 = self.uc.create_action_host_group(name="Service Group", owner=self.service)
        self.uc.create_action_host_group(name="Service Group #2", owner=self.service)
        component_group = self.uc.create_action_host_group(name="Component Group", owner=self.component)
        self.uc.add_hosts_to_action_host_group(group_id=component_group.id, hosts=[self.hosts[0].id, self.hosts[1].id])

        response = self.client.v2[self.cluster, "mapping"].post(data=[])
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        with self.subTest(msg="hosts are UNMAPPED FROM THE CLUSTER SUCCESS"):
            for target, group, groups_left_amount in (
                (self.service, service_group_1, 2),
                (self.component, component_group, 1),
            ):
                self.assertEqual(
                    ActionHostGroup.objects.filter(object_id=target.id, object_type=target.content_type).count(),
                    groups_left_amount,
                )
                self.assertEqual(
                    group.hosts.count(),
                    0,
                )
            self.assertEqual(cluster_group.hosts.count(), 1)
        with self.subTest(msg="host is REMOVED FROM THE CLUSTER SUCCESS"):
            response = self.client.v2[self.cluster, "hosts", self.hosts[0]].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            self.assertEqual(
                ActionHostGroup.objects.filter(
                    object_id=self.cluster.id, object_type=self.cluster.content_type
                ).count(),
                1,
            )
            self.assertEqual(
                cluster_group.hosts.count(),
                0,
            )

    def test_retrieve_success(self) -> None:
        name = "aWeSOME Group NAmE"
        host_1, host_2, host_3, *_ = self.hosts
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(host, self.component) for host in self.hosts])
        another_group = self.uc.create_action_host_group(name=f"{name}XXX21321", owner=self.service, description="hoho")
        service_group = self.uc.create_action_host_group(name=name, owner=self.service)
        self.uc.add_hosts_to_action_host_group(group_id=service_group.id, hosts=[host_1.id, host_3.id])
        self.uc.add_hosts_to_action_host_group(group_id=another_group.id, hosts=[host_1.id, host_2.id])

        response = self.client.v2[service_group].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": service_group.id,
                "name": name,
                "description": "",
                "hosts": [
                    {"id": host_1.id, "name": host_1.fqdn},
                    {"id": host_3.id, "name": host_3.fqdn},
                ],
            },
        )

    def test_list_success(self) -> None:
        name_1 = "compo Group 1"
        name_2 = "comPOnent gorup 123"
        name_3 = "tired fantasies"
        description = "nananan"

        service, *_ = self.uc.add_services_to_cluster(["second"], cluster=self.cluster)
        another_component = service.components.first()

        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=[(host, self.component) for host in self.hosts] + [(self.hosts[1], another_component)],
        )

        self.uc.create_action_host_group(name="Cluster Group", owner=self.cluster)
        self.uc.create_action_host_group(name="Service Group", owner=self.service)
        self.uc.create_action_host_group(name="Service Group #2", owner=self.service)
        component_group_1 = self.uc.create_action_host_group(name=name_1, owner=self.component)
        component_group_2 = self.uc.create_action_host_group(name=name_2, owner=self.component, description=description)
        another_component_group = self.uc.create_action_host_group(
            name=name_2, owner=another_component, description=description
        )
        component_group_3 = self.uc.create_action_host_group(name=name_3, owner=self.component, description=description)
        self.uc.add_hosts_to_action_host_group(
            group_id=component_group_1.id, hosts=[self.hosts[0].id, self.hosts[2].id]
        )
        self.uc.add_hosts_to_action_host_group(group_id=component_group_3.id, hosts=[self.hosts[0].id])
        self.uc.add_hosts_to_action_host_group(group_id=another_component_group.id, hosts=[self.hosts[1].id])

        # amount of queries checked on no host group -- it's the same
        # When there aren't any components, there will be 1 more query (for concerns prefetch),
        # SELECT "django_content_type"."id", "django_content_type"."app_label", "django_content_type"."model" FROM
        # "django_content_type" INNER JOIN "auth_permission" ON
        # ("django_content_type"."id" = "auth_permission"."content_type_id") WHERE
        # ("django_content_type"."app_label" = 'cm' AND "auth_permission"."codename" = 'view_component') LIMIT 21
        # yet amount of queries won't increase when more instances/components arrive
        with self.assertNumQueries(7):
            response = self.client.v2[self.component, ACTION_HOST_GROUPS].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(
            data["results"],
            [
                {
                    "id": component_group_1.id,
                    "name": name_1,
                    "description": "",
                    "hosts": [
                        {"id": self.hosts[0].id, "name": self.hosts[0].fqdn},
                        {"id": self.hosts[2].id, "name": self.hosts[2].fqdn},
                    ],
                },
                {
                    "id": component_group_2.id,
                    "name": name_2,
                    "description": description,
                    "hosts": [],
                },
                {
                    "id": component_group_3.id,
                    "name": name_3,
                    "description": description,
                    "hosts": [{"id": self.hosts[0].id, "name": self.hosts[0].fqdn}],
                },
            ],
        )

    def test_filter_groups_success(self) -> None:
        host_1, host_2, host_3, *_ = self.hosts

        cluster_group = self.uc.create_action_host_group(name="Cluster Group", owner=self.cluster)
        group_1 = self.uc.create_action_host_group(
            name="Service Group", owner=self.service, description="some description"
        )
        group_2 = self.uc.create_action_host_group(name="Super Custom", owner=self.service, description="another text")
        group_3 = self.uc.create_action_host_group(
            name="Service Group #2", owner=self.service, description="some description 2"
        )

        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(host, self.component) for host in self.hosts])

        self.uc.add_hosts_to_action_host_group(cluster_group.id, hosts=[host_1.id, host_2.id, host_3.id])
        self.uc.add_hosts_to_action_host_group(group_1.id, hosts=[host_1.id, host_2.id])
        self.uc.add_hosts_to_action_host_group(group_2.id, hosts=[host_2.id, host_3.id])
        self.uc.add_hosts_to_action_host_group(group_3.id, hosts=[host_1.id])

        endpoint = self.client.v2[self.service, ACTION_HOST_GROUPS]

        with self.subTest("Filter by Name"):
            response = endpoint.get(query={"name": "group"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_1.id, group_3.id])

            response = endpoint.get(query={"name": "er c"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_2.id])

        with self.subTest("Filter by Host"):
            response = endpoint.get(query={"hasHost": "3"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(response.json()["results"], [])

            response = endpoint.get(query={"hasHost": "0"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_1.id, group_3.id])

        with self.subTest("Filter by Name AND Host"):
            response = endpoint.get(query={"hasHost": "0", "name": "#2"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_3.id])

        with self.subTest("Filter hosts by Name"):
            response = self.client.v2[self.service, ACTION_HOST_GROUPS, group_1.pk, "hosts"].get(
                query={"name": "host-0"}
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(response.json(), [{"id": self.hosts[0].id, "name": "host-0"}])

    def test_adcm_5931_duplicates_when_filtering_by_has_host(self) -> None:
        host_1, host_2, *_ = self.hosts
        host_3 = self.uc.add_host(provider=host_1.provider, fqdn="special", cluster=self.cluster)

        group_1 = self.uc.create_action_host_group(name="Service Group", owner=self.service)
        group_2 = self.uc.create_action_host_group(name="Super Custom", owner=self.service)
        group_3 = self.uc.create_action_host_group(name="Super Custom #2", owner=self.service)

        self.uc.set_hostcomponent(
            cluster=self.cluster, entries=[(host, self.component) for host in (host_1, host_2, host_3)]
        )

        self.uc.add_hosts_to_action_host_group(group_1.id, hosts=[host_1.id, host_2.id])
        self.uc.add_hosts_to_action_host_group(group_2.id, hosts=[host_1.id, host_3.id, host_2.id])
        self.uc.add_hosts_to_action_host_group(group_3.id, hosts=[host_3.id])

        with self.subTest("Only hasHost filter"):
            response = self.client.v2[self.service, ACTION_HOST_GROUPS].get(query={"hasHost": "host"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_1.id, group_2.id])

        with self.subTest("Name and hasHost filter"):
            response = self.client.v2[self.service, ACTION_HOST_GROUPS].get(query={"hasHost": "host", "name": "Super"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(list(map(itemgetter("id"), response.json()["results"])), [group_2.id])

    def test_host_candidates_success(self) -> None:
        host_1, host_2, host_3 = self.hosts
        host_1_data, host_2_data, host_3_data = ({"id": host.id, "name": host.fqdn} for host in self.hosts)
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(host_1, self.component), (host_2, self.component)])

        cluster_group = self.uc.create_action_host_group(name="Some Taken", owner=self.cluster)
        cluster_group_2 = self.uc.create_action_host_group(name="None Taken", owner=self.cluster)
        service_group = self.uc.create_action_host_group(name="One Taken", owner=self.service)
        component_group = self.uc.create_action_host_group(name="None Taken", owner=self.component)

        self.uc.add_hosts_to_action_host_group(group_id=cluster_group.id, hosts=[host_1.id, host_2.id])
        self.uc.add_hosts_to_action_host_group(group_id=service_group.id, hosts=[host_1.id])

        for target, expected in (
            (cluster_group, [host_3_data]),
            (cluster_group_2, [host_1_data, host_2_data, host_3_data]),
            (service_group, [host_2_data]),
            (component_group, [host_1_data, host_2_data]),
        ):
            type_ = orm_object_to_core_type(target.object)

            with self.subTest(f"[{type_.name}] {target.name} Expect {len(expected)}"):
                response = self.client.v2[target, "host-candidates"].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json(), expected)

        for target, expected in (
            (self.cluster, [host_1_data, host_2_data, host_3_data]),
            (self.service, [host_1_data, host_2_data]),
            (self.component, [host_1_data, host_2_data]),
        ):
            type_ = orm_object_to_core_type(target)

            with self.subTest(f"[{type_.name}] Own {target.name} Expect {len(expected)}"):
                response = self.client.v2[target, ACTION_HOST_GROUPS, "host-candidates"].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json(), expected)

    def test_adcm_5689_string_pk_500(self) -> None:
        response = self.client.v2[self.cluster, ACTION_HOST_GROUPS, "s"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)


class TestHostsInActionHostGroup(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_action_host_group")

        cls.cluster = cls.service = cls.component = None
        for i in range(2):
            cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name=f"Cluster {i}")
            cls.service, *_ = cls.uc.add_services_to_cluster(["example"], cluster=cls.cluster)
            cls.component = cls.service.components.first()

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Provider")
        cls.hosts = [cls.uc.add_host(provider=cls.provider, fqdn=f"host-{i}") for i in range(5)]

        cls.service_2, *_ = cls.uc.add_services_to_cluster(["second"], cluster=cls.cluster)
        cls.component_2, cls.component_3 = cls.service_2.components.all()

        for host in cls.hosts[:3]:
            cls.uc.add_host_to_cluster(cluster=cls.cluster, host=host)

        cls.uc.set_hostcomponent(
            cluster=cls.cluster,
            entries=(
                (cls.hosts[0], cls.component),
                (cls.hosts[1], cls.component),
                (cls.hosts[0], cls.component_2),
            ),
        )

        objects = (cls.cluster, cls.service, cls.component, cls.service_2, cls.component_2, cls.component_3)
        cls.group_map: dict[Cluster | Service | Component, ActionHostGroup] = {
            object_: cls.uc.create_action_host_group(owner=object_, name=f"Group for {object_.name}")
            for object_ in objects
        }
        cls.user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(user_data=cls.user_credentials)

    def setUp(self) -> None:
        super().setUp()

        self.user_client = self.client_class()
        self.user_client.login(**self.user_credentials)

    def test_list_hosts_in_group_success(self) -> None:
        host_1, host_2, *_ = self.hosts
        expected = [{"id": host_1.id, "name": host_1.name}, {"id": host_2.id, "name": host_2.name}]

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            with self.subTest(f"[{type_.name}] {target.name} Expect {len(expected)}"):
                self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])

                response = self.client.v2[group, "hosts"].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json(), expected)

    def test_retrieve_host_from_group_success(self) -> None:
        host_1, host_2, *_ = self.hosts
        expected = {"id": host_1.id, "name": host_1.name}

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            with self.subTest(f"[{type_.name}] {target.name} Expect {len(expected)}"):
                self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])

                response = self.client.v2[group, "hosts", host_1.pk].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["id"], host_1.pk)

    def test_retrieve_host_from_group_not_found_fail(self) -> None:
        host_1, host_2, host_3, *_ = self.hosts

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            with self.subTest(f"[{type_.name}] {target.name} Expect Not Found"):
                self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])

                response = self.client.v2[group, "hosts", host_3.pk].get()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_host_from_group_permission_denied(self) -> None:
        self.user_client.login(**self.user_credentials)
        host_1, host_2, *_ = self.hosts

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            with self.subTest(f"[{type_.name}] {target.name} Expect Permission Denied"):
                self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])

                response = self.user_client.v2[group, "hosts", host_1.pk].get()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_add_host_to_group(self) -> None:
        host_1, host_2, host_3, host_4, *_ = self.hosts

        # todo ?
        action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        for target in (self.cluster, self.service, self.component):
            type_ = orm_object_to_core_type(target)
            group = self.group_map[target]

            # request and check is out of subtests, because success of it is crucial for all subtests later
            response = self.client.v2[group, "hosts"].post(data={"hostId": host_1.id})
            self.assertEqual(
                response.status_code,
                HTTP_201_CREATED,
                f"Host add failed for {type_.name} with status {response.status_code}",
            )

            with self.subTest(f"[{type_.name}] Add Host SUCCESS"):
                hosts_in_group = action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 1)
                self.assertEqual(hosts_in_group[0].id, host_1.id)

            with self.subTest(f"[{type_.name}] Add Host Audit {type_.name} SUCCESS"):
                self.check_last_audit_record(
                    operation_name=f"Host {host_1.fqdn} added to action host group {group.name}",
                    operation_type="update",
                    operation_result="success",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

            with self.subTest(f"[{type_.name}] Add Host Duplicate FAIL"):
                response = self.client.v2[group, "hosts"].post(data={"hostId": host_1.id})
                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(len(action_host_group_service.retrieve(group.id).hosts), 1)
                self.assertIn("hosts are already in action group", response.json()["desc"])

            with self.subTest(f"[{type_.name}] Add Host Duplicate Audit FAIL"):
                self.check_last_audit_record(
                    operation_name=f"Host {host_1.fqdn} added to action host group {group.name}",
                    operation_type="update",
                    operation_result="fail",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

        with self.subTest("[SERVICE] Add Second Host SUCCESS"):
            group = self.group_map[self.service]
            response = self.client.v2[group, "hosts"].post(data={"hostId": host_2.id})

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(len(action_host_group_service.retrieve(group.id).hosts), 2)

        for target, unmapped_host, expected_host_count in (
            (self.cluster, host_4, 1),
            (self.service, host_3, 2),
            (self.service_2, host_2, 0),
            (self.component_3, host_1, 0),
        ):
            type_ = orm_object_to_core_type(target)
            group = self.group_map[target]

            with self.subTest(f"[{type_.name}] Add Unmapped Host {unmapped_host.fqdn} FAIL"):
                response = self.client.v2[group, "hosts"].post(data={"hostId": unmapped_host.id})

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(len(action_host_group_service.retrieve(group.id).hosts), expected_host_count)

        with self.subTest("[SERVICE] Add Non Existing Host FAIL"):
            group = self.group_map[self.service]
            response = self.client.v2[self.group_map[self.service], "hosts"].post(
                data={"hostId": self.get_non_existent_pk(Host)}
            )

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("[SERVICE] Add Non Existing Host Audit FAIL"):
            self.check_last_audit_record(
                operation_name=f"Host added to action host group {group.name}",
                operation_type="update",
                operation_result="fail",
                **self.prepare_audit_object_arguments(expected_object=group),
            )

    def test_remove_host_from_group(self) -> None:
        host_1, host_2, *_ = self.hosts

        # todo ?
        action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            endpoint = self.client.v2[group, "hosts", host_1]

            self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])

            with self.subTest(f"[{type_.name}] Remove Host SUCCESS"):
                response = endpoint.delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                hosts_in_group = action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 1)
                self.assertEqual(hosts_in_group[0].id, host_2.id)

            with self.subTest(f"[{type_.name}] Remove Host Audit SUCCESS"):
                self.check_last_audit_record(
                    operation_name=f"Host {host_1.fqdn} removed from action host group {group.name}",
                    operation_type="update",
                    operation_result="success",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

            with self.subTest(f"[{type_.name}] Remove Removed Host FAIL"):
                response = endpoint.delete()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(len(action_host_group_service.retrieve(group.id).hosts), 1)

            with self.subTest(f"[{type_.name}] Remove Removed Host Audit FAIL"):
                self.check_last_audit_record(
                    operation_name=f"Host {host_1.fqdn} removed from action host group {group.name}",
                    operation_type="update",
                    operation_result="fail",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

            with self.subTest(f"[{type_.name}] Remove Last Host SUCCESS"):
                response = self.client.v2[group, "hosts", host_2].delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                hosts_in_group = action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 0)

    def test_same_hosts_in_group_of_one_object_success(self) -> None:
        host_1, host_2, *_ = self.hosts

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            second_group = self.uc.create_action_host_group(owner=target, name="Another Group")

            with self.subTest(type_.name):
                for host in (host_1, host_2):
                    response_first_group = self.client.v2[group, "hosts"].post(data={"hostId": host.id})
                    response_second_group = self.client.v2[second_group, "hosts"].post(data={"hostId": host.id})

                    self.assertEqual(response_first_group.status_code, HTTP_201_CREATED)
                    self.assertEqual(response_second_group.status_code, HTTP_201_CREATED)


class TestActionsOnActionHostGroup(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_action_host_group")

        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Cluster Bombaster")
        cls.service, *_ = cls.uc.add_services_to_cluster(["example"], cluster=cls.cluster)
        cls.component = cls.service.components.first()

        objects = (cls.cluster, cls.service, cls.component)
        cls.group_map: dict[Cluster | Service | Component, ActionHostGroup] = {
            object_: cls.uc.create_action_host_group(
                name=f"Group for {object_.name}", owner=object_, description="wait for action"
            )
            for object_ in objects
        }

    def test_get(self) -> None:
        regular_actions = ["regular"]

        for target, expected in (
            (self.cluster, ["allowed_in_group_1"]),
            (self.service, ["allowed_in_group_1", "allowed_from_service"]),
            (self.component, ["allowed_in_group_1", "allowed_from_component"]),
        ):
            group = self.group_map[target]
            type_name = orm_object_to_core_type(target).name
            group_action = Action.objects.get(prototype=target.prototype, name="allowed_in_group_1")
            regular_action = Action.objects.get(prototype=target.prototype, name="regular")

            with self.subTest(f"[{type_name}] Group List SUCCESS"):
                response = self.client.v2[group, "actions"].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                actual_action_names = sorted(map(itemgetter("name"), response.json()))
                self.assertEqual(actual_action_names, sorted(expected))

            with self.subTest(f"[{type_name}] Group Retrieve SUCCESS"):
                response = self.client.v2[group, "actions", group_action].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                data = response.json()
                self.assertEqual(data["id"], group_action.id)
                self.assertEqual(data["displayName"], group_action.display_name)

            with self.subTest(f"[{type_name}] Group Retrieve FAIL"):
                response = self.client.v2[group, "actions", regular_action].get()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            with self.subTest(f"[{type_name}] Own List Include Group Actions SUCCESS"):
                response = self.client.v2[target, "actions"].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                actual_action_names = sorted(map(itemgetter("name"), response.json()))
                self.assertEqual(actual_action_names, sorted(expected + regular_actions))

            with self.subTest(f"[{type_name}] Own Retrieve Include Group Actions SUCCESS"):
                response = self.client.v2[target, "actions", group_action].get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                data = response.json()
                self.assertEqual(data["id"], group_action.id)
                self.assertEqual(data["displayName"], group_action.display_name)

    def test_run(self) -> None:
        provider = self.uc.add_provider(bundle=self.provider_bundle, name="Provider")
        host_1, host_2 = (self.uc.add_host(provider=provider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(2))
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(host_1, self.component), (host_2, self.component)])

        for target, action_name in (
            (self.cluster, "allowed_in_group_1"),
            (self.service, "allowed_from_service"),
            (self.component, "allowed_from_component"),
        ):
            group = self.group_map[target]
            self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id])
            type_name = orm_object_to_core_type(target).name
            action = Action.objects.get(prototype=target.prototype, name=action_name)
            expected_lock_error_message = f"group #{group.id}, because it has running task: "

            for action_run_target, message_name in ((group, f"{type_name} Group"), (target, type_name)):
                # cleanup
                ConcernItem.objects.all().delete()
                TaskLog.objects.all().delete()

                response = self.client.v2[action_run_target, "actions", action, "run"].post(
                    data={"configuration": {"config": {"val": 4}, "adcmMeta": {}}}
                )

                self.assertEqual(response.status_code, HTTP_200_OK)

                with self.subTest(f"[{message_name}] Run SUCCESS"):
                    task_id = self.task_runner.expect_task_launched().id
                    task = TaskLog.objects.get(id=task_id)
                    self.assertEqual(task.task_object, action_run_target)

                with self.subTest(f"[{message_name}] Run Audit SUCCESS"):
                    self.check_last_audit_record(
                        operation_name=f"{action.display_name} action launched",
                        operation_type="update",
                        operation_result="success",
                        **self.prepare_audit_object_arguments(expected_object=action_run_target),
                    )

                with self.subTest(f"[{message_name}] Running Task Add Hosts FAIL"):
                    response = self.client.v2[group, "hosts"].post(data={"hostId": host_2.id})

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't add hosts to {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Add Hosts Audit FAIL"):
                    self.check_last_audit_record(
                        operation_name=f"Host {host_2.fqdn} added to action host group {group.name}",
                        operation_type="update",
                        operation_result="fail",
                        **self.prepare_audit_object_arguments(expected_object=group),
                    )

                with self.subTest(f"[{message_name}] Running Task Remove Hosts FAIL"):
                    response = self.client.v2[group, "hosts", host_1].delete()

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't remove hosts from {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Remove Hosts Audit FAIL"):
                    self.check_last_audit_record(
                        operation_name=f"Host {host_1.fqdn} removed from action host group {group.name}",
                        operation_type="update",
                        operation_result="fail",
                        **self.prepare_audit_object_arguments(expected_object=group),
                    )

                with self.subTest(f"[{message_name}] Running Task Delete Group FAIL"):
                    response = self.client.v2[group].delete()

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't delete {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Delete Group Audit FAIL"):
                    self.check_last_audit_record(
                        operation_name=f"{group.name} action host group deleted",
                        operation_type="delete",
                        operation_result="fail",
                        **self.prepare_audit_object_arguments(expected_object=target),
                    )

                with self.subTest(f"[{message_name}] Running Task Create New Group SUCCESS"):
                    response = self.client.v2[target, ACTION_HOST_GROUPS].post(
                        data={"name": f"New Best Group Ever {message_name}", "description": "That's it"}
                    )

                    self.assertEqual(response.status_code, HTTP_201_CREATED)

                with self.subTest(f"[{message_name}] Finish Task Audit SUCCESS"):
                    self.task_runner.run_launched_task()

                    self.check_last_audit_record(
                        operation_name=f"{action.display_name} action completed",
                        operation_type="update",
                        operation_result="success",
                        user__username=None,
                        **self.prepare_audit_object_arguments(expected_object=action_run_target),
                    )

    def test_adcm_6790_download_logs_ahg(self) -> None:
        provider = self.uc.add_provider(bundle=self.provider_bundle, name="Provider")
        host_1, host_2 = (self.uc.add_host(provider=provider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(2))
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(host_1, self.component), (host_2, self.component)])

        group = self.group_map[self.cluster]
        self.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[host_1.id, host_2.id])
        action = Action.objects.get(prototype=self.cluster.prototype, name="allowed_in_group_1")

        response = self.client.v2[group, "actions", action, "run"].post(
            data={"configuration": {"config": {"val": 4}, "adcmMeta": {}}}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched().id

        response = (self.client.v2 / "tasks" / task_id / "logs" / "download").get()

        self.assertEqual(response.status_code, HTTP_200_OK)


class TestActionHostGroupRBAC(ADCMDjangoAPISuite):
    suite_setup = SETUP_WITH_RBAC

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_action_host_group")

        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Cluster")
        cls.service, *_ = cls.uc.add_services_to_cluster(["example"], cluster=cls.cluster)
        cls.component = cls.service.components.first()

        cls.control_cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Control Cluster")
        cls.control_service, *_ = cls.uc.add_services_to_cluster(["example"], cluster=cls.control_cluster)
        cls.control_component = cls.control_service.components.first()

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Provider")
        cls.host_1, cls.host_2 = (
            cls.uc.add_host(provider=cls.provider, fqdn=f"host-{i}", cluster=cls.cluster) for i in range(2)
        )
        cls.host_3, cls.host_4 = (
            cls.uc.add_host(provider=cls.provider, fqdn=f"control-host-{i}", cluster=cls.control_cluster)
            for i in range(2)
        )

        cls.uc.set_hostcomponent(
            cluster=cls.cluster, entries=[(cls.host_1, cls.component), (cls.host_2, cls.component)]
        )
        cls.uc.set_hostcomponent(
            cluster=cls.control_cluster,
            entries=[(cls.host_3, cls.control_component), (cls.host_4, cls.control_component)],
        )

        cls.group_map: dict[Cluster | Service | Component, ActionHostGroup] = {
            object_: cls.uc.create_action_host_group(name=f"Group for {object_.name}", owner=object_)
            for object_ in (cls.cluster, cls.service, cls.component)
        }
        for group in cls.group_map.values():
            cls.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[cls.host_2.id])

        cls.control_group_map: dict[Cluster | Service | Component, ActionHostGroup] = {
            object_: cls.uc.create_action_host_group(name=f"Group for {object_.name}", owner=object_)
            for object_ in (cls.control_cluster, cls.control_service, cls.control_component)
        }
        for group in cls.control_group_map.values():
            cls.uc.add_hosts_to_action_host_group(group_id=group.id, hosts=[cls.host_3.id])

        cls.user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.user = cls.uc.create_user(user_data=cls.user_credentials)

    def setUp(self) -> None:
        super().setUp()

        self.user_client = self.client_class()
        self.user_client.login(**self.user_credentials)

    @contextmanager
    def grant_permissions_to_run_actions(self):
        # let user see 1 exact action on each object
        actions_role = role_create(
            display_name="Run action of action host group",
            child=list(Role.objects.filter(name__contains="allowed_in_group_1", type="business")),
        )
        group = create(name_to_display="Group for actions policy", user_set=[{"id": self.user.pk}])
        policies = [
            policy_create(
                name=f"Action Policy for {target.__class__.__name__}", role=actions_role, group=[group], object=[target]
            )
            for target in self.group_map
        ]

        yield

        for object_ in (*policies, actions_role, group):
            object_.delete()

    def test_no_perms_or_cluster_view_no_access(self) -> None:
        for context, name in (
            (
                self.grant_permissions(to=self.user, on=self.cluster, role_name="View cluster configurations"),
                "Cluster View",
            ),
            (nullcontext(), "No Perms"),
        ):
            with context:
                for target, group in chain.from_iterable((self.group_map.items(), self.control_group_map.items())):
                    action = Action.objects.get(prototype=target.prototype, name="allowed_in_group_1")

                    for ep, disallowed_method in (
                        (self.user_client.v2[group], "get"),
                        (self.user_client.v2[group], "patch"),
                        (self.user_client.v2[group, "host-candidates"], "get"),
                        (self.user_client.v2[group, "actions"], "get"),
                        (self.user_client.v2[group, "actions", action], "get"),
                        (self.user_client.v2[group, "actions", action, "run"], "post"),
                        (self.user_client.v2[group, "hosts"], "post"),
                        (self.user_client.v2[group, "hosts", self.host_2.id], "delete"),
                        (self.user_client.v2[group, "hosts", self.host_3.id], "delete"),
                        (self.user_client.v2[group], "delete"),
                    ):
                        with self.subTest(f"{name} | {disallowed_method.upper()} {ep.path} - 404"):
                            response = getattr(ep, disallowed_method)()
                            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_view_role_on_cluster_access(self) -> None:
        with self.grant_permissions_to_run_actions(), self.grant_permissions(
            to=self.user, on=self.cluster, role_name="View action host groups"
        ):
            for target, group in self.group_map.items():
                action = Action.objects.get(prototype=target.prototype, name="allowed_in_group_1")

                for allowed_to_view_ep in (
                    self.user_client.v2[target, ACTION_HOST_GROUPS],
                    self.user_client.v2[target, ACTION_HOST_GROUPS, "host-candidates"],
                    self.user_client.v2[group],
                    self.user_client.v2[group, "host-candidates"],
                    self.user_client.v2[group, "actions"],
                    self.user_client.v2[group, "actions", action],
                ):
                    with self.subTest(f"GET {allowed_to_view_ep.path} - 200"):
                        response = allowed_to_view_ep.get()
                        self.assertEqual(response.status_code, HTTP_200_OK)

                for ep, disallowed_method in (
                    (self.user_client.v2[target, ACTION_HOST_GROUPS], "post"),
                    (self.user_client.v2[group], "patch"),
                    (self.user_client.v2[group, "hosts"], "post"),
                    (self.user_client.v2[group, "hosts", self.host_2.id], "delete"),
                    (self.user_client.v2[group], "delete"),
                ):
                    with self.subTest(f"{disallowed_method.upper()} {ep.path} - 403"):
                        response = getattr(ep, disallowed_method)()
                        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            for target, group in self.control_group_map.items():
                action = Action.objects.get(prototype=target.prototype, name="allowed_in_group_1")

                for ep, disallowed_method in (
                    (self.user_client.v2[group], "get"),
                    (self.user_client.v2[group], "patch"),
                    (self.user_client.v2[group, "host-candidates"], "get"),
                    (self.user_client.v2[group, "actions"], "get"),
                    (self.user_client.v2[group, "actions", action], "get"),
                    (self.user_client.v2[target, ACTION_HOST_GROUPS, "host-candidates"], "get"),
                    (self.user_client.v2[target, ACTION_HOST_GROUPS], "post"),
                    (self.user_client.v2[group, "actions", action, "run"], "post"),
                    (self.user_client.v2[group, "hosts"], "post"),
                    (self.user_client.v2[group, "hosts", self.host_3.id], "delete"),
                    (self.user_client.v2[group], "delete"),
                ):
                    with self.subTest(f"{disallowed_method.upper()} {ep.path} - 404"):
                        response = getattr(ep, disallowed_method)()
                        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_edit_role_on_service_access(self) -> None:
        with self.grant_permissions(to=self.user, on=self.service, role_name="Manage action host groups"):
            for target in (self.service, self.component):
                type_name = orm_object_to_core_type(target).name
                group = self.group_map[target]
                action = Action.objects.get(prototype=target.prototype, name="allowed_in_group_1")

                with self.subTest(f"[{type_name}] GET EPs"):
                    for ep in (
                        self.user_client.v2[target, ACTION_HOST_GROUPS],
                        self.user_client.v2[target, ACTION_HOST_GROUPS, "host-candidates"],
                        self.user_client.v2[group],
                        self.user_client.v2[group, "host-candidates"],
                    ):
                        self.assertEqual(ep.get().status_code, HTTP_200_OK)

                with self.subTest(f"[{type_name}] GET Actions No Run Perms"):
                    response = self.user_client.v2[group, "actions"].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(len(response.json()), 0)

                    response = self.user_client.v2[group, "actions", action].get()
                    self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

                with self.grant_permissions_to_run_actions():
                    with self.subTest(f"[{type_name}] GET Actions With Run Perms"):
                        response = self.user_client.v2[group, "actions"].get()
                        self.assertEqual(response.status_code, HTTP_200_OK)
                        data = response.json()
                        self.assertEqual(len(data), 1)
                        self.assertEqual(data[0]["name"], action.name)

                        response = self.user_client.v2[group, "actions", action].get()
                        self.assertEqual(response.status_code, HTTP_200_OK)

                    with self.subTest(f"[{type_name}] RUN Action With Run Perms"):
                        response = self.user_client.v2[group, "actions", action, "run"].post(
                            data={"configuration": {"config": {"val": 2}, "adcmMeta": {}}}
                        )
                        self.assertEqual(response.status_code, HTTP_200_OK)

                    ConcernItem.objects.all().delete()
                    TaskLog.objects.all().delete()

                with self.subTest(f"[{type_name}] Create/Delete Group"):
                    response = self.user_client.v2[target, ACTION_HOST_GROUPS].post(
                        data={"name": "bestcool", "description": ""}
                    )
                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    new_group_id = response.json()["id"]
                    response = self.user_client.v2[target, ACTION_HOST_GROUPS, new_group_id].delete()
                    self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

                with self.subTest(f"[{type_name}] Edit Group Hosts"):
                    response = self.user_client.v2[group, "hosts"].post(data={"hostId": self.host_1.id})
                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    response = self.user_client.v2[group, "hosts", self.host_1].delete()
                    self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                    response = self.user_client.v2[group].patch(data={"description": "aljk"})
                    self.assertEqual(response.status_code, HTTP_200_OK)

            with self.subTest("No edit/view on cluster's groups"):
                target = self.cluster
                group = self.group_map[target]

                response = self.user_client.v2[target, ACTION_HOST_GROUPS].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

                response = self.user_client.v2[target, ACTION_HOST_GROUPS, "host-candidates"].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

                response = self.user_client.v2[target, ACTION_HOST_GROUPS].post()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

                for ep, disallowed_method in (
                    (self.user_client.v2[group], "get"),
                    (self.user_client.v2[group], "patch"),
                    (self.user_client.v2[group, "host-candidates"], "get"),
                    (self.user_client.v2[group, "actions"], "get"),
                    (self.user_client.v2[group, "actions", action], "get"),
                    (self.user_client.v2[group, "actions", action, "run"], "post"),
                    (self.user_client.v2[group, "hosts"], "post"),
                    (self.user_client.v2[group, "hosts", self.host_2.id], "delete"),
                    (self.user_client.v2[group, "hosts", self.host_3.id], "delete"),
                    (self.user_client.v2[group], "delete"),
                ):
                    response = getattr(ep, disallowed_method)()
                    self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_built_in_roles(self) -> None:
        with self.grant_permissions(to=self.user, on=[], role_name="ADCM User"), self.subTest("ADCM User"):
            response = self.user_client.v2[self.control_cluster, ACTION_HOST_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.user_client.v2[self.control_cluster, ACTION_HOST_GROUPS].post()
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response = self.user_client.v2[self.control_group_map[self.control_service], "actions"].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertListEqual(response.json(), [])

            action = Action.objects.get(prototype=self.control_service.prototype, name="allowed_from_service")
            response = self.user_client.v2[
                self.control_group_map[self.control_service], "actions", action, "run"
            ].post()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.grant_permissions(to=self.user, on=self.cluster, role_name="Cluster Administrator"), self.subTest(
            "Cluster Admin"
        ):
            response = self.user_client.v2[self.control_cluster, ACTION_HOST_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.user_client.v2[self.group_map[self.cluster], "hosts", self.host_2].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            response = self.user_client.v2[self.group_map[self.service], "hosts"].post(data={"hostId": self.host_1.id})
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            action = Action.objects.get(prototype=self.component.prototype, name="allowed_from_component")
            response = self.user_client.v2[self.group_map[self.component], "actions", action, "run"].post(
                data={"configuration": {"config": {"val": 3}, "adcmMeta": {}}}
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

        ConcernItem.objects.all().delete()
        TaskLog.objects.all().delete()

        with self.grant_permissions(to=self.user, on=self.service, role_name="Service Administrator"), self.subTest(
            "Service Admin"
        ):
            response = self.user_client.v2[self.cluster, ACTION_HOST_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response = self.user_client.v2[self.cluster, ACTION_HOST_GROUPS].post()
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response = self.user_client.v2[self.group_map[self.service], "actions"].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 2)

            response = self.user_client.v2[self.group_map[self.component], "hosts", self.host_2].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            response = self.user_client.v2[self.group_map[self.cluster], "actions"].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.user_client.v2[self.group_map[self.service], "actions"].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(
                sorted(entry["name"] for entry in response.json()), ["allowed_from_service", "allowed_in_group_1"]
            )

            response = self.user_client.v2[self.group_map[self.component], "actions"].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(
                sorted(entry["name"] for entry in response.json()), ["allowed_from_component", "allowed_in_group_1"]
            )

    def test_audit_with_rbac(self) -> None:
        expect_denied = partial(
            self.check_last_audit_record, operation_result="denied", user__username=self.user.username
        )

        grant_view_role = self.grant_permissions(to=self.user, on=self.cluster, role_name="View action host groups")

        for subtest_name, context, expected_code in (
            ("View Only Permissions - Denied", grant_view_role, HTTP_403_FORBIDDEN),
            ("No Permissions - Denied", nullcontext(), HTTP_404_NOT_FOUND),
        ):
            with context, self.subTest(subtest_name):
                response = self.user_client.v2[self.cluster, ACTION_HOST_GROUPS].post()
                self.assertEqual(response.status_code, expected_code)

                expect_denied(
                    operation_name="action host group created",
                    operation_type="create",
                    **self.prepare_audit_object_arguments(expected_object=self.cluster),
                )

                group = self.group_map[self.service]
                response = self.user_client.v2[group, "hosts"].post()
                self.assertEqual(response.status_code, expected_code)

                expect_denied(
                    operation_name=f"Host added to action host group {group.name}",
                    operation_type="update",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

                group = self.group_map[self.component]
                response = self.user_client.v2[group, "hosts", self.host_2].delete()
                self.assertEqual(response.status_code, expected_code)

                expect_denied(
                    operation_name=f"Host {self.host_2.fqdn} removed from action host group {group.name}",
                    operation_type="update",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )

                action = Action.objects.get(prototype=self.service.prototype, name="allowed_in_group_1")
                group = self.group_map[self.service]
                response = self.user_client.v2[group, "actions", action, "run"].post()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

                expect_denied(
                    operation_name=f"{action.display_name} action launched",
                    operation_type="update",
                    **self.prepare_audit_object_arguments(expected_object=group),
                )
