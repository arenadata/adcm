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

from contextlib import contextmanager
from operator import itemgetter
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Callable, Iterable
import random
import string
import tarfile

from api_v2.generic.config.utils import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from api_v2.prototype.utils import accept_license
from api_v2.service.utils import bulk_add_services_to_cluster
from cm.api import add_cluster, add_host, add_host_provider, add_host_to_cluster, update_obj_config
from cm.bundle import prepare_bundle, process_file
from cm.converters import orm_object_to_core_type
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    ADCMModel,
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    ObjectConfig,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.job.prepare import prepare_task_for_action
from cm.services.mapping import change_host_component_mapping
from cm.utils import deep_merge
from core.cluster.types import HostComponentEntry
from core.job.dto import TaskPayloadDTO
from core.job.types import Task
from core.rbac.dto import UserCreateDTO
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from init_db import init
from rbac.models import Group, Policy, Role, RoleTypes, User
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.services.user import perform_user_creation
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

APPLICATION_JSON = "application/json"


class TestUserCreateDTO(UserCreateDTO):
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    is_superuser: bool = False

    password: str = ""


class ParallelReadyTestCase:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.directories = cls._prepare_temporal_directories_for_adcm()
        override_settings(**cls.directories)(cls)

    @staticmethod
    def _prepare_temporal_directories_for_adcm() -> dict:
        stack = Path(mkdtemp())
        data = Path(mkdtemp()) / "data"

        temporary_directories = {
            "STACK_DIR": stack,
            "BUNDLE_DIR": stack / "data" / "bundle",
            "DOWNLOAD_DIR": Path(stack, "data", "download"),
            "DATA_DIR": data,
            "RUN_DIR": data / "run",
            "FILE_DIR": stack / "data" / "file",
            "LOG_DIR": data / "log",
            "VAR_DIR": data / "var",
            "TMP_DIR": data / "tmp",
        }

        for directory in temporary_directories.values():
            directory.mkdir(exist_ok=True, parents=True)

        return temporary_directories


class BundleLogicMixin:
    @staticmethod
    def prepare_bundle_file(source_dir: Path, target_dir: Path | None = None) -> str:
        bundle_file = f"{source_dir.name}.tar"
        with tarfile.open((target_dir or settings.DOWNLOAD_DIR) / bundle_file, "w") as tar:
            for file in source_dir.iterdir():
                tar.add(name=file, arcname=file.name)

        return bundle_file

    @atomic()
    def add_bundle(self, source_dir: Path) -> Bundle:
        bundle_file = self.prepare_bundle_file(source_dir=source_dir)
        bundle_hash, path = process_file(bundle_file=bundle_file)
        return prepare_bundle(bundle_file=bundle_file, bundle_hash=bundle_hash, path=path)


class TestCaseWithCommonSetUpTearDown(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(__file__).parent.parent.parent.parent

        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def tearDown(self) -> None:
        dirs_to_clear = (
            *Path(settings.BUNDLE_DIR).iterdir(),
            *Path(settings.DOWNLOAD_DIR).iterdir(),
            *Path(settings.FILE_DIR).iterdir(),
            *Path(settings.LOG_DIR).iterdir(),
            *Path(settings.RUN_DIR).iterdir(),
        )
        for item in dirs_to_clear:
            if item.is_dir():
                rmtree(item)
            else:
                if item.name != ".gitkeep":
                    item.unlink()


class BaseTestCase(TestCaseWithCommonSetUpTearDown, ParallelReadyTestCase, BundleLogicMixin):
    def setUp(self) -> None:
        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"

        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            is_superuser=True,
        )
        self.test_user_group = Group.objects.create(name="simple_test_group")
        self.test_user_group.user_set.add(self.test_user)

        self.no_rights_user_username = "no_rights_user"
        self.no_rights_user_password = "no_rights_user_password"
        self.no_rights_user = User.objects.create_user(
            username="no_rights_user",
            password="no_rights_user_password",
        )
        self.no_rights_user_group = Group.objects.create(name="no_right_group")
        self.no_rights_user_group.user_set.add(self.no_rights_user)

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.login()

    def login(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    @property
    @contextmanager
    def no_rights_user_logged_in(self):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": self.no_rights_user_username,
                "password": self.no_rights_user_password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    @contextmanager
    def another_user_logged_in(self, username: str, password: str):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    def another_user_log_in(self, username: str, password: str):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def get_new_user(self, username: str, password: str, group_pk: int | None = None) -> User:
        data = {"username": username, "password": password}
        if group_pk:
            data["group"] = [{"id": group_pk}]

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data=data,
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return User.objects.get(pk=response.json()["id"])

    def get_role_data(self, role_name: str) -> dict:
        response: Response = self.client.get(
            path=reverse(viewname="v1:rbac:role-list"),
            data={"name": role_name, "type": "role", "view": "interface"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return response.json()["results"][0]

    def create_policy(
        self,
        role_name: str,
        obj: ADCMEntity,
        group_pk: int | None = None,
    ) -> int:
        role_data = self.get_role_data(role_name=role_name)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:policy-list"),
            data={
                "name": f"test_policy_{obj.prototype.type}_{obj.pk}_admin",
                "role": {"id": role_data["id"]},
                "group": [{"id": group_pk}],
                "object": [{"name": obj.name, "type": obj.prototype.type, "id": obj.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return response.json()["id"]

    def create_role(
        self,
        role_name: str,
        parametrized_by_type: list[ObjectType],
        children_names: list[str],
    ) -> Role:
        request_data = {
            "name": role_name,
            "display_name": role_name,
            "type": RoleTypes.ROLE,
            "parametrized_by_type": parametrized_by_type,
            "child": [],
        }
        for child_name in children_names:
            response: Response = self.client.get(
                path=reverse(viewname="v1:rbac:role-list"),
                data={"name": child_name},
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

            request_data["child"].append({"id": response.json()["results"][0]["id"]})

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:role-list"),
            data=request_data,
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Role.objects.get(pk=response.json()["id"])

    def upload_bundle(self, path: Path) -> None:
        with open(path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def load_bundle(self, path: Path) -> Bundle:
        response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return Bundle.objects.get(pk=response.data["id"])

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        self.upload_bundle(path=path)

        return self.load_bundle(path=path)

    def create_cluster(self, bundle_pk: int, name: str) -> Cluster:
        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={
                "prototype_id": Prototype.objects.get(bundle_id=bundle_pk, type=ObjectType.CLUSTER).pk,
                "name": name,
                "display_name": name,
                "bundle_id": bundle_pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Cluster.objects.get(pk=response.json()["id"])

    def create_service(self, cluster_pk: int, name: str) -> ClusterObject:
        response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_pk}),
            data={"prototype_id": Prototype.objects.get(name=name).pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return ClusterObject.objects.get(pk=response.json()["id"])

    def upload_bundle_create_cluster_config_log(
        self, bundle_path: Path, cluster_name: str = "test-cluster"
    ) -> tuple[Bundle, Cluster, ConfigLog]:
        bundle = self.upload_and_load_bundle(path=bundle_path)
        cluster = self.create_cluster(bundle_pk=bundle.pk, name=cluster_name)

        return bundle, cluster, ConfigLog.objects.get(obj_ref=cluster.config)

    def create_provider(self, bundle_path: Path, name: str) -> HostProvider:
        bundle = self.upload_and_load_bundle(path=bundle_path)

        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER).pk,
                "name": name,
                "display_name": name,
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return HostProvider.objects.get(pk=response.json()["id"])

    def create_host_in_cluster(self, provider_pk: int, name: str, cluster_pk: int) -> Host:
        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": provider_pk}),
            data={"fqdn": name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host = Host.objects.get(pk=response.json()["id"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_pk}),
            data={"host_id": host.pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return host

    def create_new_config(self, config_data: dict) -> ObjectConfig:
        config = ObjectConfig.objects.create(current=1, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config=config_data)
        config.current = config_log.pk
        config.save(update_fields=["current"])
        return config

    @staticmethod
    def get_hostcomponent_data(service_pk: int, host_pk: int) -> list[dict[str, int]]:
        hostcomponent_data = []
        for component in ServiceComponent.objects.filter(service_id=service_pk):
            hostcomponent_data.append({"component_id": component.pk, "host_id": host_pk, "service_id": service_pk})

        return hostcomponent_data

    def create_hostcomponent(self, cluster_pk: int, hostcomponent_data: list[dict[str, int]]):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_pk}),
            data={"cluster_id": cluster_pk, "hc": hostcomponent_data},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    @staticmethod
    def get_random_str_num(length: int) -> str:
        return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))


class BusinessLogicMixin(BundleLogicMixin):
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

    def add_host(
        self,
        provider: HostProvider,
        fqdn: str,
        description: str = "",
        cluster: Cluster | None = None,
        bundle: Bundle | None = None,
    ) -> Host:
        prototype = Prototype.objects.filter(bundle=bundle or provider.prototype.bundle, type=ObjectType.HOST).first()
        host = add_host(prototype=prototype, provider=provider, fqdn=fqdn, description=description)
        if cluster is not None:
            self.add_host_to_cluster(cluster=cluster, host=host)

        return host

    @staticmethod
    def add_host_to_cluster(cluster: Cluster, host: Host) -> Host:
        return add_host_to_cluster(cluster=cluster, host=host)

    @staticmethod
    def add_services_to_cluster(service_names: list[str], cluster: Cluster) -> QuerySet[ClusterObject]:
        service_prototypes = Prototype.objects.filter(
            type=ObjectType.SERVICE, name__in=service_names, bundle=cluster.prototype.bundle
        )
        return bulk_add_services_to_cluster(cluster=cluster, prototypes=service_prototypes)

    @staticmethod
    def set_hostcomponent(cluster: Cluster, entries: Iterable[tuple[Host, ServiceComponent]]) -> list[HostComponent]:
        change_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=host.id, component_id=component.id) for host, component in entries
            ),
        )
        return list(HostComponent.objects.filter(cluster_id=cluster.id))

    @staticmethod
    def get_non_existent_pk(model: type[ADCMEntity | ADCMModel | User | Role | Group | Policy]):
        try:
            return model.objects.order_by("-pk").first().pk + 1
        except model.DoesNotExist:
            return 1

    def create_user(self, user_data: dict | None = None, **kwargs) -> User:
        user_data = (user_data or {}) | kwargs
        if not user_data:
            user_data = {
                "username": "test_user_username",
                "password": "test_user_password",
                "email": "testuser@mail.ru",
                "first_name": "test_user_first_name",
                "last_name": "test_user_last_name",
                "profile": "",
            }

        groups = tuple(map(itemgetter("id"), user_data.pop("groups", None) or ()))

        user_id = perform_user_creation(create_data=TestUserCreateDTO(**user_data), groups=groups)

        return User.objects.get(id=user_id)

    @contextmanager
    def grant_permissions(self, to: User, on: list[ADCMEntity] | ADCMEntity, role_name: str):
        if not isinstance(on, list):
            on = [on]

        group = create_group(name_to_display=f"Group for role `{role_name}`", user_set=[{"id": to.pk}])
        target_role = Role.objects.get(name=role_name)
        delete_role = True

        if target_role.type != RoleTypes.ROLE:
            custom_role = role_create(display_name=f"Custom `{role_name}` role", child=[target_role])
        else:
            custom_role = target_role
            delete_role = False

        policy = policy_create(name=f"Policy for role `{role_name}`", role=custom_role, group=[group], object=on)

        yield

        policy.delete()
        if delete_role:
            custom_role.delete()
        group.delete()

    @staticmethod
    def change_configuration(
        target: ADCMModel | GroupConfig,
        config_diff: dict,
        meta_diff: dict | None = None,
        preprocess_config: Callable[[dict], dict] = lambda x: x,
    ) -> ConfigLog:
        meta = meta_diff or {}

        target.refresh_from_db()
        current_config = ConfigLog.objects.get(id=target.config.current)

        updated = update_obj_config(
            obj_conf=target.config,
            config=deep_merge(origin=preprocess_config(current_config.config), renovator=config_diff),
            attr=convert_adcm_meta_to_attr(
                deep_merge(origin=convert_attr_to_adcm_meta(current_config.attr), renovator=meta)
            ),
            description="",
        )
        target.refresh_from_db()

        return updated


class TaskTestMixin:
    def prepare_task(
        self,
        owner: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
        payload: TaskPayloadDTO | None = None,
        host: Host | None = None,
        **action_search_kwargs,
    ) -> Task:
        owner_descriptor = CoreObjectDescriptor(id=owner.id, type=orm_object_to_core_type(owner))
        action = Action.objects.get(prototype_id=owner.prototype_id, **action_search_kwargs)
        target = owner_descriptor if not host else CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST)
        return prepare_task_for_action(
            target=target, owner=owner_descriptor, action=action.id, payload=payload or TaskPayloadDTO()
        )
