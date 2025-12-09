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
import uuid
import random
import shutil
import string
import tarfile

from api_v2.prototype.utils import accept_license
from api_v2.service.utils import bulk_add_services_to_cluster
from cm.converters import orm_object_to_core_type
from cm.legacy.api import add_cluster, add_host, add_host_provider, add_host_to_cluster, update_obj_config
from cm.legacy.services.bundle_alt.load import Directories, parse_bundle_archive
from cm.legacy.services.config import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from cm.legacy.services.job.action import prepare_task_for_action
from cm.legacy.services.mapping import set_host_component_mapping
from cm.legacy.utils import deep_merge
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    ADCMModel,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    ObjectConfig,
    ObjectType,
    Prototype,
    Provider,
    Service,
)
from core.legacy.cluster.types import HostComponentEntry
from core.legacy.job.dto import TaskPayloadDTO
from core.legacy.job.types import Task
from core.legacy.rbac.dto import UserCreateDTO
from core.legacy.rbac.operations import add_user_to_groups
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.test import Client, TestCase, override_settings
from infra.services import get_config_service
from init_db import init
from rbac.models import Group, Policy, Role, RoleTypes, User
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.services.user import GroupDB, UserDB, create_new_user, perform_user_creation
from rbac.upgrade.role import init_roles

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
        override_settings(**cls.directories, ANSIBLE_SECRET="verysecretstuff")(cls)

    @staticmethod
    def _prepare_temporal_directories_for_adcm() -> dict[str, Path]:
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
        if source_dir.is_dir():
            archive = self.prepare_bundle_file(source_dir=source_dir)
            archive_path = settings.DOWNLOAD_DIR / archive
        else:
            # for "easy" backward compatibility with "upload_and_load_bundle"
            # which accepted path to already packed archive
            archive_path = source_dir

        return parse_bundle_archive(
            archive=archive_path,
            directories=Directories(
                downloads=settings.DOWNLOAD_DIR, bundles=settings.BUNDLE_DIR, files=settings.FILE_DIR
            ),
            adcm_version=settings.ADCM_VERSION,
            verified_signature_only=False,
        )


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
        # TODO: ADCM-7513
        get_config_service.cache_clear()

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
        # it may not be all correct since it used API based login, now Django based
        self.client.login(username=self.test_user_username, password=self.test_user_password)

    @property
    @contextmanager
    def no_rights_user_logged_in(self):
        # it may not be all correct since it used API based login, now Django based
        self.client.logout()

        with self.another_user_logged_in(username=self.no_rights_user_username, password=self.no_rights_user_password):
            yield

    @contextmanager
    def another_user_logged_in(self, username: str, password: str):
        self.client.login(username=username, password=password)

        yield

        self.login()

    def get_new_user(self, username: str, password: str, group_pk: int | None = None) -> User:
        data = UserCreateDTO(
            username=username, password=password, email="", first_name="", last_name="", is_superuser=False
        )
        user_id = create_new_user(data=data, db=UserDB, password_requirements=None)
        if group_pk:
            add_user_to_groups(user_id=user_id, groups=[group_pk], db=GroupDB)

        return User.objects.get(pk=user_id)

    def create_policy(
        self,
        role_name: str,
        obj: ADCMEntity,
        group_pk: int | None = None,
    ) -> int:
        policy_name = f"test_policy_{obj.prototype.type}_{obj.pk}_admin"
        role = Role.objects.get(name=role_name)
        policy = policy_create(
            name=policy_name, role=role, group=[Group.objects.get(id=group_pk)] if group_pk else None, object=[obj]
        )
        return policy.pk

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        downloaded_archive = Path(path.parent, str(uuid.uuid4()) + ".temp")
        shutil.copy2(path, downloaded_archive)
        return self.add_bundle(source_dir=downloaded_archive)

    def create_cluster(self, bundle_pk: int, name: str) -> Cluster:
        prototype = Prototype.objects.get(bundle_id=bundle_pk, type=ObjectType.CLUSTER)
        return add_cluster(prototype=prototype, name=name)

    def create_service(self, cluster_pk: int, name: str) -> Service:
        cluster = Cluster.objects.get(id=cluster_pk)
        prototypes = Prototype.objects.filter(name=name, bundle_id=cluster.bundle_id).all()
        return bulk_add_services_to_cluster(cluster=cluster, prototypes=prototypes).get()

    def upload_bundle_create_cluster_config_log(
        self, bundle_path: Path, cluster_name: str = "test-cluster"
    ) -> tuple[Bundle, Cluster, ConfigLog]:
        bundle = self.upload_and_load_bundle(path=bundle_path)
        cluster = self.create_cluster(bundle_pk=bundle.pk, name=cluster_name)

        return bundle, cluster, ConfigLog.objects.get(obj_ref=cluster.config)

    def create_provider(self, bundle_path: Path, name: str) -> Provider:
        bundle = self.upload_and_load_bundle(path=bundle_path)
        prototype = Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER)
        return add_host_provider(prototype=prototype, name=name)

    def create_host_in_cluster(self, provider_pk: int, name: str, cluster_pk: int) -> Host:
        provider = Provider.objects.get(pk=provider_pk)
        prototype = Prototype.objects.get(bundle_id=provider.bundle_id, type="host")
        cluster = Cluster.objects.get(pk=cluster_pk)
        host = add_host(prototype=prototype, provider=provider, fqdn=name)
        add_host_to_cluster(cluster=cluster, host=host)
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
        for component in Component.objects.filter(service_id=service_pk):
            hostcomponent_data.append({"component_id": component.pk, "host_id": host_pk, "service_id": service_pk})

        return hostcomponent_data

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
    def add_provider(bundle: Bundle, name: str, description: str = "") -> Provider:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.PROVIDER).first()
        return add_host_provider(prototype=prototype, name=name, description=description)

    def add_host(
        self,
        provider: Provider,
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
    def add_services_to_cluster(service_names: list[str], cluster: Cluster) -> QuerySet[Service]:
        service_prototypes = Prototype.objects.filter(
            type=ObjectType.SERVICE, name__in=service_names, bundle=cluster.prototype.bundle
        )
        return bulk_add_services_to_cluster(cluster=cluster, prototypes=service_prototypes)

    @staticmethod
    def set_hostcomponent(cluster: Cluster, entries: Iterable[tuple[Host, Component]]) -> list[HostComponent]:
        set_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.bundle_id,
            new_mapping=(HostComponentEntry(host_id=host.id, component_id=component.id) for host, component in entries),
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
        target: ADCMModel | ConfigHostGroup,
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
        owner: ADCM | Cluster | Service | Component | Provider | Host,
        payload: TaskPayloadDTO | None = None,
        host: Host | None = None,
        feature_scripts_jinja: bool = False,
        **action_search_kwargs,
    ) -> Task:
        owner_descriptor = CoreObjectDescriptor(id=owner.id, type=orm_object_to_core_type(owner))
        action = Action.objects.get(prototype_id=owner.prototype_id, **action_search_kwargs)
        target = owner_descriptor if not host else CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST)
        return prepare_task_for_action(
            target=target,
            orm_owner=owner,
            orm_target=host or owner,
            action=action.id,
            payload=payload or TaskPayloadDTO(),
            feature_scripts_jinja=feature_scripts_jinja,
        )
