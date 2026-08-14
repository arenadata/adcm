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
import shutil

from cm.models import (
    ADCM,
    Bundle,
    ConfigLog,
)
from init_db import init
from rbac.models import Group, User
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

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        downloaded_archive = Path(path.parent, str(uuid.uuid4()) + ".temp")
        shutil.copy2(path, downloaded_archive)
        return self.add_bundle(source_dir=downloaded_archive)
