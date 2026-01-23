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

from http.cookies import SimpleCookie
from importlib import import_module
from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
from typing import Any, Collection, Literal, TypeAlias
from unittest.mock import patch
import tarfile
import unittest

from adcm.tests.base import BusinessLogicMixin, ParallelReadyTestCase
from adcm.tests.client import ADCMTestClient
from audit.models import AuditLog, AuditObjectType, AuditSession
from cm.legacy.services.cluster import retrieve_cluster_topology, retrieve_clusters_objects_maintenance_mode
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    JobLog,
    JobStatus,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Provider,
    Service,
    TaskLog,
)
from cm.tests.mocks.task_runner import RunTaskMock
from core.legacy.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.legacy.cluster.types import ObjectMaintenanceModeState
from core.types import ClusterID
from django.conf import settings
from django.http import HttpRequest
from infra.services import get_config_service
from init_db import init
from rbac.models import Group, Policy, Role, User
from rbac.upgrade.role import init_roles
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.test import APITestCase

AuditTarget: TypeAlias = (
    Bundle | Cluster | Service | Component | ActionHostGroup | Provider | Host | User | Group | Role | Policy
)


# allow asserts
# ruff: noqa: S101


class BaseAPITestCase(APITestCase, ParallelReadyTestCase, BusinessLogicMixin):
    client: ADCMTestClient
    client_class = ADCMTestClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_bundles_dir = Path(__file__).parent / "bundles"
        cls.test_files_dir = Path(__file__).parent / "files"

        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(id=adcm.config.current)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def setUp(self) -> None:
        # TODO: ADCM-7513
        get_config_service.cache_clear()

        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"
        cluster_bundle_2_path = self.test_bundles_dir / "cluster_two"
        provider_bundle_path = self.test_bundles_dir / "provider"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_2_path)
        self.provider_bundle = self.add_bundle(source_dir=provider_bundle_path)

        self.cluster_1 = self.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")
        self.cluster_2 = self.add_cluster(bundle=self.bundle_2, name="cluster_2", description="cluster_2")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider", description="provider")

    def tearDown(self) -> None:
        dirs_to_clear = (
            *Path(settings.BUNDLE_DIR).iterdir(),
            *Path(settings.DOWNLOAD_DIR).iterdir(),
            *Path(settings.FILE_DIR).iterdir(),
            *Path(settings.LOG_DIR).iterdir(),
            *Path(settings.RUN_DIR).iterdir(),
            *Path(settings.VAR_DIR).iterdir(),
        )

        for item in dirs_to_clear:
            if item.is_dir():
                rmtree(item)
            else:
                if item.name != ".gitkeep":
                    item.unlink()

    def check_last_audit_record(
        self,
        model: type[AuditLog | AuditSession] = AuditLog,
        *,
        expect_object_changes_: bool = True,
        **kwargs,
    ) -> AuditLog:
        last_audit_record = model.objects.order_by("pk").last()
        self.assertIsNotNone(last_audit_record, f"{model.__name__} table is empty")

        # we always want to check who performed the audited action
        if model is AuditLog:
            kwargs.setdefault("user__username", "admin")

        object_changes = kwargs.pop("object_changes", {})

        expected_record = model.objects.filter(**kwargs).order_by("pk").last()
        self.assertIsNotNone(expected_record, "Can't find audit record")
        self.assertEqual(last_audit_record.pk, expected_record.pk, "Expected audit record is not last")

        # Object changes are {} for most cases,
        # we always want to check it, but providing it each time is redundant.
        # But sometimes structure is too complex for sqlite/ORM to handle,
        # so we have to check changes separately.
        #
        # Check is on equality after retrieve for more clear message
        # and to avoid object changes filtering
        # SQLite support ended in release 2.7.0. We need to review this code.
        if (model is AuditLog) and expect_object_changes_:
            self.assertDictEqual(expected_record.object_changes, object_changes)

        return last_audit_record

    @staticmethod
    def get_most_recent_audit_log() -> AuditLog | None:
        """Mostly for debug purposes"""
        return AuditLog.objects.order_by("pk").last()

    def prepare_audit_object_arguments(
        self,
        expected_object: AuditTarget | None,
        *,
        is_deleted: bool = False,
    ) -> dict[str, Any]:
        if expected_object is None:
            return {"audit_object__isnull": True}

        if isinstance(expected_object, ActionHostGroup):
            owner_name = self.prepare_audit_object_arguments(expected_object=expected_object.object)[
                "audit_object__object_name"
            ]
            name = f"{owner_name}/{expected_object.name}"
            type_ = AuditObjectType.ACTION_HOST_GROUP
        elif isinstance(expected_object, Component):
            name = (
                f"{expected_object.cluster.name}/{expected_object.service.display_name}/{expected_object.display_name}"
            )
            type_ = "component"
        elif isinstance(expected_object, Service):
            name = f"{expected_object.cluster.name}/{expected_object.display_name}"
            type_ = "service"
        elif isinstance(expected_object, Host):
            name = expected_object.fqdn
            type_ = "host"
        elif isinstance(expected_object, Group):
            name = expected_object.name
            type_ = "group"
        elif isinstance(expected_object, Role):
            name = expected_object.name
            type_ = "role"
        else:
            name = getattr(expected_object, "display_name", expected_object.name)
            type_ = expected_object.__class__.__name__.lower()

        return {
            "audit_object__object_id": expected_object.pk,
            "audit_object__object_name": name,
            "audit_object__object_type": type_,
            "audit_object__is_deleted": is_deleted,
        }

    @property
    def session(self):
        """Return the current session variables."""
        engine = import_module(settings.SESSION_ENGINE)
        cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            return engine.SessionStore(cookie.value)
        session = engine.SessionStore()
        session.save()
        self.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session

    def logout(self):
        """Log out the user by removing the cookies and session object."""
        from django.contrib.auth import get_user, logout

        request = HttpRequest()
        if self.session:
            request.session = self.session
            request.user = get_user(request)
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        logout(request)
        self.cookies = SimpleCookie()

    def simulate_finished_task(self, object_: Cluster | Service | Component, action: Action) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": [], "description": ""}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()

        return run_task.target_task, run_task.target_task.joblog_set.last()

    def simulate_running_task(self, object_: Cluster | Service | Component, action: Action) -> (TaskLog, JobLog):
        with RunTaskMock() as run_task:
            (self.client.v2[object_] / "actions" / action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": [], "description": ""}
            )

        run_task.run()
        run_task.target_task.refresh_from_db()
        task = run_task.target_task
        job = task.joblog_set.last()
        task.status = JobStatus.RUNNING
        task.save(update_fields=["status"])
        job.status = JobStatus.RUNNING
        job.pid = 5_000_000
        job.save(update_fields=["status", "pid"])

        return task, job


# Reasonably fast and dirty approach to "duplicate" test for another use case with a bit less overhead
def subtests_on_feature_flag(tc: unittest.TestCase, flag_func, override_in: str):
    name = flag_func.__name__
    # todo REMOVE IN ADCM-7319
    for flag_value in (False,):
        with patch(f"{override_in}.{name}", return_value=flag_value):
            yield tc.subTest(f"{name}-{flag_value}")


class APIV2Mixin:
    client: ADCMTestClient

    def _prepare_bundle_file(self, src: Path, dst: Path) -> Path:
        with tarfile.open(dst, "w") as tar:
            for file in src.iterdir():
                tar.add(name=file, arcname=file.name)

        return dst

    def create_bundle(self, src: Path) -> Bundle:
        if not src.is_dir():
            raise ValueError(f"Not a dir: {src}")

        dst = (Path(gettempdir()) / src.name).with_suffix(".tar")
        archive = self._prepare_bundle_file(src=src, dst=dst)

        with archive.open(encoding="utf-8") as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")
        assert response.status_code == HTTP_201_CREATED, f"Bundle `{archive}` upload failed: {response.status_code}"

        return Bundle.objects.get(id=response.json()["id"])

    def create_cluster(self, bundle: Bundle, name: str, description: str = "", accept_license: bool = True) -> Cluster:
        prototype = Prototype.objects.only("id", "license").get(bundle=bundle, type=ObjectType.CLUSTER)
        if prototype.license == "unaccepted" and accept_license:
            response = self.client.v2[prototype, "license", "accept"].post()
            assert response.status_code == HTTP_200_OK, f"Accept license failed: {response.status_code}"

        response = (self.client.v2 / "clusters").post(
            data={"prototypeId": prototype.id, "name": name, "description": description}
        )
        assert response.status_code == HTTP_201_CREATED, f"Cluster creation failed: {response.status_code}"

        return Cluster.objects.get(id=response.json()["id"])

    def create_services(self, names: Collection[str], cluster: Cluster) -> list[Service]:
        bundle_id = cluster.prototype.bundle_id
        prototype_ids = Prototype.objects.values_list("id", flat=True).filter(
            name__in=names, type=ObjectType.SERVICE, bundle_id=bundle_id
        )
        response = self.client.v2[cluster, "services"].post(data=[{"prototype_id": id_} for id_ in prototype_ids])
        assert response.status_code == HTTP_201_CREATED, f"Service creation failed: {response.status_code}"

        return list(Service.objects.filter(id__in=[r["id"] for r in response.json()]))

    def create_mapping(self, cluster: Cluster, entries: Collection[tuple[Host, Component]]) -> None:
        response = self.client.v2[cluster, "mapping"].post(
            data=[{"hostId": host.id, "componentId": component.id} for host, component in entries]
        )
        assert response.status_code == HTTP_201_CREATED, f"Mapping creation failed: {response.status_code}"

    def create_provider(self, bundle: Bundle, name: str, description: str = "") -> Provider:
        prototype_id = Prototype.objects.values_list("id", flat=True).get(bundle=bundle, type=ObjectType.PROVIDER)
        response = (self.client.v2 / "hostproviders").post(
            data={"prototypeId": prototype_id, "name": name, "description": description},
        )
        assert response.status_code == HTTP_201_CREATED, f"Provider creation failed: {response.status_code}"

        return Provider.objects.get(id=response.json()["id"])

    def create_host(self, provider: Provider, name: str, cluster: Cluster | None = None) -> Host:
        data = {"hostproviderId": provider.id, "name": name}
        if cluster:
            data["clusterId"] = cluster.id
        response = (self.client.v2 / "hosts").post(data=data)
        assert response.status_code == HTTP_201_CREATED, f"Host creation failed: {response.status_code}"

        return Host.objects.get(id=response.json()["id"])

    def create_action_host_group(
        self, owner: Cluster | Service | Component, name: str, hosts: Collection[Host] = (), description: str = ""
    ) -> ActionHostGroup:
        response = self.client.v2[owner, "action-host-groups"].post(data={"name": name, "description": description})
        assert response.status_code == HTTP_201_CREATED, f"ActionHostGroup creation failed: {response.status_code}"

        ahg = ActionHostGroup.objects.get(id=response.json()["id"])

        for host in hosts:
            response = self.client.v2[ahg, "hosts"].post(data={"hostId": host.id})
            assert response.status_code == HTTP_201_CREATED, f"Add host to {ahg} failed: {response.status_code}"

        return ahg

    def create_config_host_group(
        self, owner: Cluster | Service | Component | Provider | Host, name: str, description: str = ""
    ) -> ConfigHostGroup:
        response = self.client.v2[owner, "config-groups"].post(data={"name": name, "description": description})
        assert response.status_code == HTTP_201_CREATED, f"ConfigHostGroup creation failed: {response.status_code}"

        return ConfigHostGroup.objects.get(id=response.json()["id"])

    def set_maintenance_mode(self, obj: Service | Component | Host, value: MaintenanceMode) -> None:
        response = self.client.v2[obj, "maintenance-mode"].post(data={"maintenance_mode": value})
        assert response.status_code == HTTP_200_OK, f"Setting maintenance mode failed: {response.status_code}"

    def run_task(
        self,
        object_: Cluster | Service | Component | Provider | Host | ActionHostGroup,
        action: Action,
        mapping: Collection[tuple[Host, Component]] = (),
        config: dict[Literal["config", "adcmMeta"], dict] | None = None,
        expected_code: int = HTTP_200_OK,
        **mock_kwargs,
    ) -> RunTaskMock:
        hc = {"hostComponentMap": [{"hostId": host.id, "componentId": component.id} for host, component in mapping]}
        config = config or {"config": {}, "adcmMeta": {}}

        with RunTaskMock(**mock_kwargs) as run_task:
            response = self.client.v2[object_, "actions", action, "run"].post(data={"isVerbose": False, **config, **hc})

        assert response.status_code == expected_code, f"Unexpected run result: {response.status_code}"

        return run_task


class TestUtilsMixin:
    def check_mm_is_on_only_for(self, obj: Component | Host | None, cluster_id: ClusterID):
        objects_mm = calculate_maintenance_mode_for_cluster_objects(
            topology=retrieve_cluster_topology(cluster_id=cluster_id),
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=(cluster_id,)),
        )
        components_mm = objects_mm.components
        hosts_mm = objects_mm.hosts

        if isinstance(obj, Component):
            self.assertEqual(components_mm.pop(obj.id), ObjectMaintenanceModeState.ON)
        elif isinstance(obj, Host):
            self.assertEqual(hosts_mm.pop(obj.id), ObjectMaintenanceModeState.ON)
        elif obj is None:
            pass
        else:
            raise ValueError(f"Unexpected object type: {type(obj)}")

        self.assertSetEqual(set(objects_mm.services.values()), {ObjectMaintenanceModeState.OFF})
        self.assertSetEqual(set(components_mm.values()), {ObjectMaintenanceModeState.OFF})
        self.assertSetEqual(set(hosts_mm.values()), {ObjectMaintenanceModeState.OFF})
