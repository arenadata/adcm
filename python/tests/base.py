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
from pathlib import Path
import uuid
import random
import shutil
import string

from cm.legacy.api import add_cluster, add_host, add_host_provider, add_host_to_cluster
from cm.models import (
    ADCM,
    ADCMEntity,
    Bundle,
    Cluster,
    Component,
    ConfigLog,
    Host,
    ObjectConfig,
    ObjectType,
    Prototype,
    Provider,
)
from core.legacy.rbac.dto import UserCreateDTO
from core.legacy.rbac.operations import add_user_to_groups
from init_db import init
from rbac.models import Group, Role, User
from rbac.services.policy import policy_create
from rbac.services.user import GroupDB, UserDB, create_new_user
from rbac.upgrade.role import init_roles
import dishka
import django.test

from tests._base import WithIndependentDirectories
from tests.dependencies import get_default_overridden_providers, get_task_runner_manager
from tests.deprecated import BundleLogicMixin
from tests.use_cases import UseCases

APPLICATION_JSON = "application/json"


# todo fix


class WithPreparedFSAndInitADCM(django.test.SimpleTestCase, WithIndependentDirectories):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._create_directories_on_fs()

        cls.base_dir = Path(__file__).parent.parent.parent

        container = dishka.make_container(*get_default_overridden_providers())

        init_roles()
        init(container=container)

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

        cls.uc = UseCases(container=container)

    def tearDown(self) -> None:
        super().tearDown()

        self._clean_directories()


class BaseTestCase(django.test.TestCase, WithPreparedFSAndInitADCM, BundleLogicMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.task_runner = get_task_runner_manager()

    def setUp(self) -> None:
        super().setUp()

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

        self.client = django.test.Client(HTTP_USER_AGENT="Mozilla/5.0")
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
