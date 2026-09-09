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

from cm.converters import orm_object_to_core_type
from cm.legacy.services.concern.flags import BuiltInFlag, ConcernFlag, raise_flag, raise_flag_for_process
from cm.legacy.services.concern.locks import create_task_flag_concern, create_task_lock_concern
from cm.models import Action, ADCMEntity, Cluster, ConcernCause, ConcernItem, ConcernType, Host, JobLog, TaskLog
from core.concern.repo import ConcernRepoI
from core.types import ADCMCoreType, CoreObjectDescriptor, Descriptor
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT
from tests.client import ADCMTestClient
from tests.dependencies import get_status_scenarios_manager
from tests.suites import TEST_API_V2_BUNDLES_DIR, GenericTestCase


class TestConcernsOnRename(GenericTestCase):
    """
    Cluster/host rename must update names stored in placeholders of concerns that point at renamed object
    and leave placeholders of all other objects untouched.
    """

    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient

    CLUSTER_NAME = "require_dummy_service"
    NEW_CLUSTER_NAME = "renamed_cluster"
    HOST_FQDN = "concerned-host"
    NEW_HOST_FQDN = "renamed-host"
    REQUIRED_SERVICE_NAME = "required"
    ACTION_NAME = "dummy"
    TWIN_NAME = "twin-name"

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        cls.cluster_bundle = cls.uc.upload_bundle(src=TEST_API_V2_BUNDLES_DIR / "cluster_all_concerns")
        cls.provider_bundle = cls.uc.upload_bundle(src=TEST_API_V2_BUNDLES_DIR / "provider_concerns")

        # cluster is named after service prototype on purpose:
        # concerns of both have `cluster_services` placeholder type, so type tells them apart in no way
        cls.cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name=cls.CLUSTER_NAME)
        # `main` is added to get an issue with host-component mapping on cluster
        cls.uc.add_services_to_cluster(names=["require_dummy_service", "main"], cluster=cls.cluster)
        cls.service = cls.cluster.services.get(prototype__name="require_dummy_service")

        cls.control_cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="control_cluster")

        # named as prototype of service required by bundle: it is a `target` of cluster's "required service" issue
        cls.cluster_named_as_prototype = cls.uc.add_cluster(bundle=cls.cluster_bundle, name=cls.REQUIRED_SERVICE_NAME)
        # named as action of its own prototype: it is a `target` of "configuring process" flag
        cls.cluster_named_as_action = cls.uc.add_cluster(bundle=cls.cluster_bundle, name=cls.ACTION_NAME)

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Concerned HP")
        cls.host = cls.uc.add_host(provider=cls.provider, fqdn=cls.HOST_FQDN)
        cls.control_host = cls.uc.add_host(provider=cls.provider, fqdn="control-host")

        # provider and its host are named the same
        cls.twin_provider = cls.uc.add_provider(bundle=cls.provider_bundle, name=cls.TWIN_NAME)
        cls.twin_host = cls.uc.add_host(provider=cls.twin_provider, fqdn=cls.TWIN_NAME)

    def setUp(self) -> None:
        super().setUp()

        self.client.login(username="admin", password="admin")

    # helpers

    def get_own_concern(self, object_: ADCMEntity, cause: ConcernCause) -> ConcernItem:
        concern = ConcernItem.objects.filter(owner_id=object_.pk, owner_type=object_.content_type, cause=cause).first()
        self.assertIsNotNone(concern, f"No concern with cause {cause} on {object_}")
        return concern

    def get_placeholder(self, concern: ConcernItem, slot: str) -> dict:
        concern.refresh_from_db()
        placeholder = concern.reason["placeholder"]
        self.assertIn(slot, placeholder)
        return placeholder[slot]

    def rename_cluster(self, cluster: Cluster, new_name: str) -> None:
        response = self.client.v2[cluster].patch(data={"name": new_name})
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

    def rename_host(self, host: Host, new_name: str) -> None:
        response = self.client.v2[host].patch(data={"name": new_name})
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

    def get_own_sources(self, object_: ADCMEntity) -> dict[ConcernCause, dict]:
        return {
            concern.cause: self.get_placeholder(concern, "source")
            for concern in ConcernItem.objects.filter(owner_id=object_.pk, owner_type=object_.content_type)
        }

    def create_task_concern(self, owner: Cluster, *, blocking: bool) -> ConcernItem:
        task = TaskLog.objects.create(
            action=Action.objects.get(prototype=owner.prototype, name=self.ACTION_NAME),
            object_id=owner.pk,
            object_type=owner.content_type,
            owner_id=owner.pk,
            owner_type=orm_object_to_core_type(owner).value,
            selector={},
            status="running",
            verbose=False,
            is_blocking=blocking,
            name=self.ACTION_NAME,
            display_name="Dummy",
        )
        # job is named as its owner on purpose: `job` placeholder must not be renamed
        JobLog.objects.create(
            task=task,
            status="running",
            name=self.ACTION_NAME,
            display_name=owner.name,
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        create_concern = create_task_lock_concern if blocking else create_task_flag_concern
        return ConcernItem.objects.get(id=create_concern(task))

    # cluster

    def test_cluster_rename_updates_own_concerns_success(self) -> None:
        concerns = {
            cause: self.get_own_concern(self.cluster, cause)
            for cause in (ConcernCause.CONFIG, ConcernCause.IMPORT, ConcernCause.SERVICE, ConcernCause.HOSTCOMPONENT)
        }

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        for cause, concern in concerns.items():
            source = self.get_placeholder(concern, "source")
            self.assertEqual(source["name"], self.NEW_CLUSTER_NAME, f"Not updated for {cause}")
            self.assertEqual(source["params"], {"cluster_id": self.cluster.pk})

    def test_cluster_rename_keeps_prototype_placeholder_success(self) -> None:
        concern = self.get_own_concern(self.cluster, ConcernCause.SERVICE)
        target_before = self.get_placeholder(concern, "target")

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "target"), target_before)

    def test_cluster_rename_keeps_service_with_same_name_success(self) -> None:
        concern = self.get_own_concern(self.service, ConcernCause.REQUIREMENT)
        source_before = self.get_placeholder(concern, "source")
        # both cluster and service placeholders have this type, only params differ
        self.assertEqual(source_before["type"], "cluster_services")
        self.assertEqual(source_before["name"], self.CLUSTER_NAME)

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "source"), source_before)

    def test_cluster_rename_keeps_action_name_in_process_flag_success(self) -> None:
        action = Action.objects.get(prototype=self.cluster.prototype, name="dummy")
        raise_flag_for_process(
            action=action,
            flag=BuiltInFlag.ACTION_PROCESS_RUNNING.value,
            on_objects=[CoreObjectDescriptor(id=self.cluster.pk, type=orm_object_to_core_type(self.cluster))],
            action_owner=self.cluster,
        )
        concern = self.get_own_concern(self.cluster, ConcernCause.CONFIGURING_PROCESS)
        target_before = self.get_placeholder(concern, "target")

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "target"), target_before)
        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_CLUSTER_NAME)

    def test_cluster_rename_keeps_other_cluster_concerns_success(self) -> None:
        concern = self.get_own_concern(self.control_cluster, ConcernCause.CONFIG)
        source_before = self.get_placeholder(concern, "source")

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "source"), source_before)

    def test_cluster_update_without_name_keeps_concerns_success(self) -> None:
        sources_before = self.get_own_sources(self.cluster)
        self.assertNotEqual(sources_before, {})

        response = self.client.v2[self.cluster].patch(data={"description": "new description"})
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

        self.assertDictEqual(self.get_own_sources(self.cluster), sources_before)

    def test_cluster_update_with_same_name_fail(self) -> None:
        # unlike host's one, cluster's update serializer is bound to no instance,
        # so unique validator rejects cluster's own name; concerns should stay untouched anyway
        sources_before = self.get_own_sources(self.cluster)
        self.assertNotEqual(sources_before, {})

        response = self.client.v2[self.cluster].patch(data={"name": self.CLUSTER_NAME})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.json())

        self.assertDictEqual(self.get_own_sources(self.cluster), sources_before)

    def test_cluster_rename_keeps_prototype_with_same_name_success(self) -> None:
        cluster = self.cluster_named_as_prototype
        concern = self.get_own_concern(cluster, ConcernCause.SERVICE)
        target_before = self.get_placeholder(concern, "target")
        self.assertEqual(target_before["name"], self.REQUIRED_SERVICE_NAME)

        self.rename_cluster(cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "target"), target_before)
        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_CLUSTER_NAME)

    def test_cluster_rename_keeps_action_with_same_name_success(self) -> None:
        cluster = self.cluster_named_as_action
        action = Action.objects.get(prototype=cluster.prototype, name=self.ACTION_NAME)
        raise_flag_for_process(
            action=action,
            flag=BuiltInFlag.ACTION_PROCESS_RUNNING.value,
            on_objects=[CoreObjectDescriptor(id=cluster.pk, type=orm_object_to_core_type(cluster))],
            action_owner=cluster,
        )
        concern = self.get_own_concern(cluster, ConcernCause.CONFIGURING_PROCESS)
        target_before = self.get_placeholder(concern, "target")
        self.assertEqual(target_before["name"], self.ACTION_NAME)

        self.rename_cluster(cluster, self.NEW_CLUSTER_NAME)

        self.assertDictEqual(self.get_placeholder(concern, "target"), target_before)
        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_CLUSTER_NAME)

    def test_cluster_rename_updates_custom_flag_success(self) -> None:
        raise_flag(
            flag=ConcernFlag(name="custom_flag", message="custom message", cause=None),
            on_objects=[CoreObjectDescriptor(id=self.cluster.pk, type=orm_object_to_core_type(self.cluster))],
        )
        concern = ConcernItem.objects.get(
            owner_id=self.cluster.pk, owner_type=self.cluster.content_type, name="custom_flag"
        )

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_CLUSTER_NAME)

    def test_cluster_lock_target_updated_by_repo_success(self) -> None:
        # lock is described by `target` placeholder, not by `source`;
        # such concerns can't be renamed via API (rename is forbidden while lock exists), so repo is called directly
        concern = self.create_task_concern(self.cluster, blocking=True)
        self.assertEqual(self.get_placeholder(concern, "target")["name"], self.CLUSTER_NAME)
        job_before = self.get_placeholder(concern, "job")
        self.assertEqual(job_before["name"], self.CLUSTER_NAME)

        self.container.get(ConcernRepoI).update_object_name_in_concerns(
            object_=Descriptor(id=self.cluster.pk, type=ADCMCoreType.CLUSTER),
            previous_name=self.CLUSTER_NAME,
            new_name=self.NEW_CLUSTER_NAME,
        )

        self.assertEqual(self.get_placeholder(concern, "target")["name"], self.NEW_CLUSTER_NAME)
        self.assertDictEqual(self.get_placeholder(concern, "job"), job_before)

    def test_cluster_rename_keeps_job_with_same_name_success(self) -> None:
        concern = self.create_task_concern(self.cluster, blocking=False)
        self.assertEqual(concern.type, ConcernType.FLAG)
        job_before = self.get_placeholder(concern, "job")
        self.assertEqual(job_before["name"], self.CLUSTER_NAME)

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_CLUSTER_NAME)
        self.assertDictEqual(self.get_placeholder(concern, "job"), job_before)

    def test_cluster_rename_notifies_about_concerns_success(self) -> None:
        concern_ids = {concern.id for concern in ConcernItem.objects.filter(owner_id=self.cluster.pk)}
        self.assertNotEqual(concern_ids, set())

        self.rename_cluster(self.cluster, self.NEW_CLUSTER_NAME)

        get_status_scenarios_manager().expect_called_once("notify_about_redistributed_concerns_from_maps")

    def test_cluster_update_without_name_does_not_notify_success(self) -> None:
        response = self.client.v2[self.cluster].patch(data={"description": "new description"})
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

        get_status_scenarios_manager().expect_not_called("notify_about_redistributed_concerns_from_maps")

    def test_distribution_of_renamed_concerns_success(self) -> None:
        concern = self.get_own_concern(self.cluster, ConcernCause.CONFIG)

        distribution = self.container.get(ConcernRepoI).get_concerns_distribution(concern_ids=[concern.id])

        self.assertDictEqual(distribution[ADCMCoreType.CLUSTER], {self.cluster.pk: {concern.id}})
        self.assertSetEqual(
            set(distribution[ADCMCoreType.SERVICE]), set(self.cluster.services.values_list("id", flat=True))
        )
        self.assertSetEqual(
            set(distribution[ADCMCoreType.COMPONENT]), set(self.cluster.components.values_list("id", flat=True))
        )

    def test_distribution_of_no_concerns_success(self) -> None:
        self.assertEqual(self.container.get(ConcernRepoI).get_concerns_distribution(concern_ids=()), {})

    # host

    def test_host_rename_updates_own_concerns_success(self) -> None:
        concern = self.get_own_concern(self.host, ConcernCause.CONFIG)

        self.rename_host(self.host, self.NEW_HOST_FQDN)

        source = self.get_placeholder(concern, "source")
        self.assertEqual(source["name"], self.NEW_HOST_FQDN)
        self.assertEqual(source["params"], {"host_id": self.host.pk, "provider_id": self.provider.pk})

    def test_host_rename_keeps_provider_and_other_host_concerns_success(self) -> None:
        provider_concern = self.get_own_concern(self.provider, ConcernCause.CONFIG)
        other_host_concern = self.get_own_concern(self.control_host, ConcernCause.CONFIG)
        provider_source_before = self.get_placeholder(provider_concern, "source")
        other_host_source_before = self.get_placeholder(other_host_concern, "source")

        self.rename_host(self.host, self.NEW_HOST_FQDN)

        self.assertDictEqual(self.get_placeholder(provider_concern, "source"), provider_source_before)
        self.assertDictEqual(self.get_placeholder(other_host_concern, "source"), other_host_source_before)

    def test_host_rename_keeps_action_name_in_process_flag_success(self) -> None:
        action = Action.objects.get(prototype=self.host.prototype, name="dummy")
        raise_flag_for_process(
            action=action,
            flag=BuiltInFlag.ACTION_PROCESS_RUNNING.value,
            on_objects=[CoreObjectDescriptor(id=self.host.pk, type=orm_object_to_core_type(self.host))],
            action_owner=self.host,
        )
        concern = self.get_own_concern(self.host, ConcernCause.CONFIGURING_PROCESS)
        target_before = self.get_placeholder(concern, "target")

        self.rename_host(self.host, self.NEW_HOST_FQDN)

        self.assertDictEqual(self.get_placeholder(concern, "target"), target_before)
        self.assertEqual(self.get_placeholder(concern, "source")["name"], self.NEW_HOST_FQDN)

    def test_host_update_without_name_keeps_concerns_success(self) -> None:
        sources_before = self.get_own_sources(self.host)
        self.assertNotEqual(sources_before, {})

        response = self.client.v2[self.host].patch(data={"description": "new description"})
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

        self.assertDictEqual(self.get_own_sources(self.host), sources_before)

    def test_host_update_with_same_name_keeps_concerns_success(self) -> None:
        sources_before = self.get_own_sources(self.host)
        self.assertNotEqual(sources_before, {})

        self.rename_host(self.host, self.HOST_FQDN)

        self.assertDictEqual(self.get_own_sources(self.host), sources_before)

    def test_host_rename_keeps_provider_with_same_name_success(self) -> None:
        provider_concern = self.get_own_concern(self.twin_provider, ConcernCause.CONFIG)
        provider_source_before = self.get_placeholder(provider_concern, "source")
        self.assertEqual(provider_source_before["name"], self.TWIN_NAME)

        self.rename_host(self.twin_host, self.NEW_HOST_FQDN)

        self.assertDictEqual(self.get_placeholder(provider_concern, "source"), provider_source_before)
        self.assertEqual(
            self.get_placeholder(self.get_own_concern(self.twin_host, ConcernCause.CONFIG), "source")["name"],
            self.NEW_HOST_FQDN,
        )
