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

from operator import itemgetter

from cm.converters import model_to_core_type, orm_object_to_core_type
from cm.models import Action, ActionHostGroup, Cluster, ClusterObject, ConcernItem, Host, ServiceComponent, TaskLog
from cm.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService, CreateDTO
from cm.tests.mocks.task_runner import RunTaskMock
from core.types import CoreObjectDescriptor
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase

ACTION_HOST_GROUPS = "action-host-groups"


class TestActionHostGroup(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        self.bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_action_host_group")

        self.cluster = self.service = self.component = None
        for i in range(3):
            self.cluster = self.add_cluster(bundle=self.bundle, name=f"Cluster {i}")
            self.service = self.add_services_to_cluster(["example"], cluster=self.cluster).get()
            self.component = self.service.servicecomponent_set.first()

        self.hostprovider = self.add_provider(bundle=self.provider_bundle, name="Provider")
        self.hosts = [
            self.add_host(provider=self.hostprovider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(3)
        ]

    def create_group(
        self, name: str, owner: Cluster | ClusterObject | ServiceComponent, description: str = ""
    ) -> ActionHostGroup:
        return ActionHostGroup.objects.get(
            id=self.action_host_group_service.create(
                CreateDTO(
                    name=name,
                    owner=CoreObjectDescriptor(id=owner.id, type=orm_object_to_core_type(owner)),
                    description=description,
                )
            )
        )

    def test_create_group_success(self) -> None:
        group_counter = 0

        for target in (self.cluster, self.service, self.component):
            type_ = model_to_core_type(target.__class__)
            group_counter += 1

            data = {"name": f"group for {type_.value}", "description": "simple group"}

            response = self.client.v2[target, ACTION_HOST_GROUPS].post(data=data)

            with self.subTest(f"[{type_.name}] CREATED SUCCESS"):
                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.assertEqual(ActionHostGroup.objects.count(), group_counter)
                created_group = ActionHostGroup.objects.filter(
                    object_id=target.id, object_type=target.content_type, name=data["name"]
                ).first()
                self.assertIsNotNone(created_group)
                self.assertEqual(response.json(), {"id": created_group.id, **data, "hosts": []})

            # todo implement
            # with self.subTest(f"[{type_.name}] AUDITED SUCCESS"):
            #     self.assertEqual(response.status_code, HTTP_201_CREATED)

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
            second_service = ClusterObject.objects.exclude(id=self.service.id).first()
            data = {"name": "cool", "description": ""}

            response = self.client.v2[self.service, ACTION_HOST_GROUPS].post(data=data)
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            response = self.client.v2[second_service, ACTION_HOST_GROUPS].post(data=data)
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            groups = sorted(
                ActionHostGroup.objects.values_list("object_id", flat=True).filter(
                    name=data["name"], object_type=ClusterObject.class_content_type
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

    def test_delete_success(self) -> None:
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.hosts[0], self.component), (self.hosts[1], self.component))
        )

        cluster_group = self.create_group(name="Cluster Group", owner=self.cluster)
        self.action_host_group_service.add_hosts_to_group(group_id=cluster_group.id, hosts=[self.hosts[0].id])
        service_group_1 = self.create_group(name="Service Group", owner=self.service)
        self.create_group(name="Service Group #2", owner=self.service)
        component_group = self.create_group(name="Component Group", owner=self.component)
        self.action_host_group_service.add_hosts_to_group(
            group_id=component_group.id, hosts=[self.hosts[0].id, self.hosts[1].id]
        )

        for target, group_to_delete, groups_left_amount in (
            (self.cluster, cluster_group, 0),
            (self.service, service_group_1, 1),
            (self.component, component_group, 0),
        ):
            with self.subTest(orm_object_to_core_type(target).name):
                response = self.client.v2[group_to_delete].delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                self.assertEqual(
                    ActionHostGroup.objects.filter(object_id=target.id, object_type=target.content_type).count(),
                    groups_left_amount,
                )

            # todo add audit

    def test_retrieve_success(self) -> None:
        name = "aWeSOME Group NAmE"
        host_1, host_2, host_3, *_ = self.hosts
        self.set_hostcomponent(cluster=self.cluster, entries=[(host, self.component) for host in self.hosts])
        another_group = self.create_group(name=f"{name}XXX21321", owner=self.service, description="hoho")
        service_group = self.create_group(name=name, owner=self.service)
        self.action_host_group_service.add_hosts_to_group(group_id=service_group.id, hosts=[host_1.id, host_3.id])
        self.action_host_group_service.add_hosts_to_group(group_id=another_group.id, hosts=[host_1.id, host_2.id])

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

        another_component = (
            self.add_services_to_cluster(["second"], cluster=self.cluster).get().servicecomponent_set.first()
        )

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=[(host, self.component) for host in self.hosts] + [(self.hosts[1], another_component)],
        )

        self.create_group(name="Cluster Group", owner=self.cluster)
        self.create_group(name="Service Group", owner=self.service)
        self.create_group(name="Service Group #2", owner=self.service)
        component_group_1 = self.create_group(name=name_1, owner=self.component)
        component_group_2 = self.create_group(name=name_2, owner=self.component, description=description)
        another_component_group = self.create_group(name=name_2, owner=another_component, description=description)
        component_group_3 = self.create_group(name=name_3, owner=self.component, description=description)
        self.action_host_group_service.add_hosts_to_group(
            group_id=component_group_1.id, hosts=[self.hosts[0].id, self.hosts[2].id]
        )
        self.action_host_group_service.add_hosts_to_group(group_id=component_group_3.id, hosts=[self.hosts[0].id])
        self.action_host_group_service.add_hosts_to_group(group_id=another_component_group.id, hosts=[self.hosts[1].id])

        # amount of queries checked on 1 component group -- it's the same
        with self.assertNumQueries(6):
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

    def test_host_candidates_success(self) -> None:
        host_1, host_2, host_3 = self.hosts
        host_1_data, host_2_data, host_3_data = ({"id": host.id, "name": host.fqdn} for host in self.hosts)
        self.set_hostcomponent(cluster=self.cluster, entries=[(host_1, self.component), (host_2, self.component)])

        cluster_group = self.create_group(name="Some Taken", owner=self.cluster)
        cluster_group_2 = self.create_group(name="None Taken", owner=self.cluster)
        service_group = self.create_group(name="One Taken", owner=self.service)
        component_group = self.create_group(name="None Taken", owner=self.component)

        self.action_host_group_service.add_hosts_to_group(group_id=cluster_group.id, hosts=[host_1.id, host_2.id])
        self.action_host_group_service.add_hosts_to_group(group_id=service_group.id, hosts=[host_1.id])

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


class TestHostsInActionHostGroup(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        self.bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_action_host_group")

        self.cluster = self.service = self.component = None
        for i in range(2):
            self.cluster = self.add_cluster(bundle=self.bundle, name=f"Cluster {i}")
            self.service = self.add_services_to_cluster(["example"], cluster=self.cluster).get()
            self.component = self.service.servicecomponent_set.first()

        self.hostprovider = self.add_provider(bundle=self.provider_bundle, name="Provider")
        self.hosts = [self.add_host(provider=self.hostprovider, fqdn=f"host-{i}") for i in range(5)]

        self.service_2 = self.add_services_to_cluster(["second"], cluster=self.cluster).get()
        self.component_2, self.component_3 = self.service_2.servicecomponent_set.all()

        for host in self.hosts[:3]:
            self.add_host_to_cluster(cluster=self.cluster, host=host)

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=(
                (self.hosts[0], self.component),
                (self.hosts[1], self.component),
                (self.hosts[0], self.component_2),
            ),
        )

        objects = (self.cluster, self.service, self.component, self.service_2, self.component_2, self.component_3)
        self.group_map: dict[Cluster | ClusterObject | ServiceComponent, ActionHostGroup] = {
            object_: ActionHostGroup.objects.get(
                id=self.action_host_group_service.create(
                    CreateDTO(
                        owner=CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_)),
                        name=f"Group for {object_.name}",
                        description="",
                    )
                )
            )
            for object_ in objects
        }

    def test_add_host_to_group(self) -> None:
        host_1, host_2, host_3, host_4, *_ = self.hosts

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
                hosts_in_group = self.action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 1)
                self.assertEqual(hosts_in_group[0].id, host_1.id)

            # todo add audit check for all success/fail cases
            # with self.subTest(f"Add Audit {type_.name} SUCCESS"):
            #     ...

            with self.subTest(f"[{type_.name}] Add Host Duplicate FAIL"):
                response = self.client.v2[group, "hosts"].post(data={"hostId": host_1.id})
                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(len(self.action_host_group_service.retrieve(group.id).hosts), 1)
                self.assertIn("hosts are already in action group", response.json()["desc"])

        with self.subTest("[SERVICE] Add Second Host SUCCESS"):
            group = self.group_map[self.service]
            response = self.client.v2[group, "hosts"].post(data={"hostId": host_2.id})

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(len(self.action_host_group_service.retrieve(group.id).hosts), 2)

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
                self.assertEqual(len(self.action_host_group_service.retrieve(group.id).hosts), expected_host_count)

        with self.subTest("[SERVICE] Add Non Existing Host FAIL"):
            response = self.client.v2[self.group_map[self.service], "hosts"].post(
                data={"hostId": self.get_non_existent_pk(Host)}
            )

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_remove_host_from_group(self) -> None:
        host_1, host_2, *_ = self.hosts

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            endpoint = self.client.v2[group, "hosts", host_1]

            self.action_host_group_service.add_hosts_to_group(group_id=group.id, hosts=[host_1.id, host_2.id])

            with self.subTest(f"[{type_.name}] Remove Host SUCCESS"):
                response = endpoint.delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                hosts_in_group = self.action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 1)
                self.assertEqual(hosts_in_group[0].id, host_2.id)

            with self.subTest(f"[{type_.name}] Remove Removed Host FAIL"):
                response = endpoint.delete()

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(len(self.action_host_group_service.retrieve(group.id).hosts), 1)

            with self.subTest(f"[{type_.name}] Remove Last Host SUCCESS"):
                response = self.client.v2[group, "hosts", host_2].delete()

                self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
                hosts_in_group = self.action_host_group_service.retrieve(group.id).hosts
                self.assertEqual(len(hosts_in_group), 0)

            # todo add audit

    def test_same_hosts_in_group_of_one_object_success(self) -> None:
        host_1, host_2, *_ = self.hosts

        for target in (self.cluster, self.service, self.component):
            group = self.group_map[target]
            type_ = orm_object_to_core_type(target)
            second_group = ActionHostGroup.objects.get(
                id=self.action_host_group_service.create(
                    CreateDTO(owner=CoreObjectDescriptor(id=target.id, type=type_), name="Another Group")
                )
            )

            with self.subTest(type_.name):
                for host in (host_1, host_2):
                    response_first_group = self.client.v2[group, "hosts"].post(data={"hostId": host.id})
                    response_second_group = self.client.v2[second_group, "hosts"].post(data={"hostId": host.id})

                    self.assertEqual(response_first_group.status_code, HTTP_201_CREATED)
                    self.assertEqual(response_second_group.status_code, HTTP_201_CREATED)


class TestActionsOnActionHostGroup(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        self.bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_action_host_group")

        self.cluster = self.add_cluster(bundle=self.bundle, name="Cluster Bombaster")
        self.service = self.add_services_to_cluster(["example"], cluster=self.cluster).get()
        self.component = self.service.servicecomponent_set.first()

        objects = (self.cluster, self.service, self.component)
        self.group_map: dict[Cluster | ClusterObject | ServiceComponent, ActionHostGroup] = {
            object_: ActionHostGroup.objects.get(
                id=self.action_host_group_service.create(
                    CreateDTO(
                        owner=CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_)),
                        name=f"Group for {object_.name}",
                        description="wait for action",
                    )
                )
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
        hostprovider = self.add_provider(bundle=self.provider_bundle, name="Provider")
        host_1, host_2 = (
            self.add_host(provider=hostprovider, fqdn=f"host-{i}", cluster=self.cluster) for i in range(2)
        )
        self.set_hostcomponent(cluster=self.cluster, entries=[(host_1, self.component), (host_2, self.component)])

        # todo add audit cases
        for target, action_name in (
            (self.cluster, "allowed_in_group_1"),
            (self.service, "allowed_from_service"),
            (self.component, "allowed_from_component"),
        ):
            group = self.group_map[target]
            self.action_host_group_service.add_hosts_to_group(group_id=group.id, hosts=[host_1.id])
            type_name = orm_object_to_core_type(target).name
            action = Action.objects.get(prototype=target.prototype, name=action_name)
            expected_lock_error_message = f"group #{group.id}, because it has running task: "

            for action_run_target, message_name in ((group, f"{type_name} Group"), (target, type_name)):
                # cleanup
                ConcernItem.objects.all().delete()
                TaskLog.objects.all().delete()

                with RunTaskMock() as run_task:
                    response = self.client.v2[action_run_target, "actions", action, "run"].post(data={})

                self.assertEqual(response.status_code, HTTP_200_OK)

                with self.subTest(f"[{message_name}] Run SUCCESS"):
                    self.assertIsNotNone(run_task.target_task)
                    self.assertEqual(run_task.target_task.task_object, action_run_target)

                with self.subTest(f"[{message_name}] Running Task Add Hosts FAIL"):
                    response = self.client.v2[group, "hosts"].post(data={"hostId": host_2.id})

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't add hosts to {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Remove Hosts FAIL"):
                    response = self.client.v2[group, "hosts", host_1].delete()

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't remove hosts from {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Delete Group FAIL"):
                    response = self.client.v2[group].delete()

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertIn(f"Can't delete {expected_lock_error_message}", response.json()["desc"])

                with self.subTest(f"[{message_name}] Running Task Create New Group SUCCESS"):
                    response = self.client.v2[target, ACTION_HOST_GROUPS].post(
                        data={"name": f"New Best Group Ever {message_name}", "description": "That's it"}
                    )

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
