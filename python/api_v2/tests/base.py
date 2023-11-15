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
import tarfile
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from typing import Any, TypeAlias, TypedDict

from api_v2.prototype.utils import accept_license
from audit.models import AuditLog
from cm.api import (
    add_cluster,
    add_hc,
    add_host,
    add_host_provider,
    add_host_to_cluster,
    add_service_to_cluster,
)
from cm.bundle import prepare_bundle, process_file
from cm.models import (
    ADCM,
    ADCMEntity,
    ADCMModel,
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from init_db import init
from rbac.models import Group, Policy, Role, User
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.services.user import create_user
from rbac.upgrade.role import init_roles
from rest_framework.test import APITestCase

from adcm.tests.base import ParallelReadyTestCase

AuditTarget: TypeAlias = (
    Bundle | Cluster | ClusterObject | ServiceComponent | HostProvider | Host | User | Group | Role | Policy
)


class HostComponentMapDictType(TypedDict):
    host_id: int
    service_id: int
    component_id: int


class BaseAPITestCase(APITestCase, ParallelReadyTestCase):
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

    @staticmethod
    def prepare_bundle_file(source_dir: Path) -> str:
        bundle_file = f"{source_dir.name}.tar"
        with tarfile.open(settings.DOWNLOAD_DIR / bundle_file, "w") as tar:
            for file in source_dir.iterdir():
                tar.add(name=file, arcname=file.name)

        return bundle_file

    def add_bundle(self, source_dir: Path) -> Bundle:
        bundle_file = self.prepare_bundle_file(source_dir=source_dir)
        bundle_hash, path = process_file(bundle_file=bundle_file)
        return prepare_bundle(bundle_file=bundle_file, bundle_hash=bundle_hash, path=path)

    @staticmethod
    def add_cluster(bundle: Bundle, name: str, description: str = "") -> Cluster:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.CLUSTER).first()
        if prototype.license_path is not None:
            accept_license(prototype=prototype)
            prototype.refresh_from_db(fields=["license"])
        return add_cluster(prototype=prototype, name=name, description=description)

    @staticmethod
    def add_provider(bundle: Bundle, name: str, description: str = "") -> HostProvider:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.PROVIDER).first()
        return add_host_provider(prototype=prototype, name=name, description=description)

    @staticmethod
    def add_host(bundle: Bundle, provider: HostProvider, fqdn: str, description: str = "") -> Host:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.HOST).first()
        return add_host(prototype=prototype, provider=provider, fqdn=fqdn, description=description)

    @staticmethod
    def add_host_to_cluster(cluster: Cluster, host: Host) -> Host:
        return add_host_to_cluster(cluster=cluster, host=host)

    @staticmethod
    def add_service_to_cluster(service_name: str, cluster: Cluster) -> ClusterObject:
        service_prototype = Prototype.objects.get(
            type=ObjectType.SERVICE, name=service_name, bundle=cluster.prototype.bundle
        )
        return add_service_to_cluster(cluster=cluster, proto=service_prototype)

    @staticmethod
    def add_hostcomponent_map(cluster: Cluster, hc_map: list[HostComponentMapDictType]) -> list[HostComponent]:
        return add_hc(cluster=cluster, hc_in=hc_map)

    @staticmethod
    def get_non_existent_pk(model: type[ADCMEntity | ADCMModel | User | Role | Group | Policy]):
        try:
            return model.objects.order_by("-pk").first().pk + 1
        except model.DoesNotExist:
            return 1

    def create_user(self, user_data: dict | None = None) -> User:
        if user_data is None:
            user_data = {
                "username": "test_user_username",
                "password": "test_user_password",
                "email": "testuser@mail.ru",
                "first_name": "test_user_first_name",
                "last_name": "test_user_last_name",
                "profile": "",
            }

        return create_user(**user_data)

    def check_last_audit_log(self, *, expect_object_changes_: bool = True, **kwargs) -> AuditLog:
        last_audit_log = AuditLog.objects.order_by("pk").last()
        self.assertIsNotNone(last_audit_log, "AuditLog table is empty")

        # we always want to check who performed the audited action
        kwargs.setdefault("user__username", "admin")

        # Object changes are {} for most cases,
        # we always want to check it, but providing it each time is redundant.
        # But sometimes structure is too complex for sqlite/ORM to handle,
        # so we have to check changes separately.
        if expect_object_changes_:
            kwargs.setdefault("object_changes", {})

        expected_log = AuditLog.objects.filter(**kwargs).order_by("pk").last()
        self.assertIsNotNone(expected_log, "Can't find audit log")
        self.assertEqual(last_audit_log.pk, expected_log.pk, "Expected audit log is not last")

        return last_audit_log

    @staticmethod
    def get_most_recent_audit_log() -> AuditLog | None:
        """Mostly for debug purposes"""
        return AuditLog.objects.order_by("pk").last()

    @staticmethod
    def prepare_audit_object_arguments(
        expected_object: AuditTarget | None,
        *,
        is_deleted: bool = False,
    ) -> dict[str, Any]:
        if expected_object is None:
            return {"audit_object__isnull": True}

        if isinstance(expected_object, ServiceComponent):
            name = (
                f"{expected_object.cluster.name}/{expected_object.service.display_name}/{expected_object.display_name}"
            )
            type_ = "component"
        elif isinstance(expected_object, ClusterObject):
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
            # replace for hostprovider
            type_ = expected_object.__class__.__name__.lower().replace("hostp", "p")

        return {
            "audit_object__object_id": expected_object.pk,
            "audit_object__object_name": name,
            "audit_object__object_type": type_,
            "audit_object__is_deleted": is_deleted,
        }

    @contextmanager
    def grant_permissions(self, to: User, on: list[ADCMEntity] | ADCMEntity, role_name: str):
        if not isinstance(on, list):
            on = [on]
        group = create_group(name_to_display=f"Group for role `{role_name}`", user_set=[{"id": to.pk}])
        custom_role = role_create(display_name=f"Custom `{role_name}` role", child=[Role.objects.get(name=role_name)])
        policy = policy_create(name=f"Policy for role `{role_name}`", role=custom_role, group=[group], object=on)

        yield

        policy.delete()
        custom_role.delete()
        group.delete()
