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

from functools import cache
from pathlib import Path
from tempfile import mkdtemp
import uuid

from adcm.tests.client import ADCMTestClient
from django.test import modify_settings, override_settings, testcases
from init_db import init
from rbac.upgrade.role import init_roles

from api_v2.tests.base import TEST_BUNDLES_DIR, TEST_FILES_DIR
from api_v2.tests.setup.overrides import get_task_runner_manager


@cache
def new_process_bound_tempdir() -> Path:
    return Path(mkdtemp())


class BaseAPITestCase(testcases.TestCase):
    """
    Obligatory part of any API v2 based test
    """

    # is required for correct type detection in test cases
    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        # override DI

        modify_settings(
            MIDDLEWARE={
                "prepend": "api_v2.tests.setup.overrides.DishkaMiddleware",
                "remove": ["api_v2.utils.di.DishkaMiddleware"],
            }
        )(cls)

        # override settings for directories (shouldn't be important after full DI change)

        root = new_process_bound_tempdir() / uuid.uuid4().hex
        cls.temporary_directories = {
            "STACK_DIR": root,
            "DATA_DIR": root,
            "BUNDLE_DIR": root / "bundle",
            "DOWNLOAD_DIR": root / "download",
            "RUN_DIR": root / "run",
            "FILE_DIR": root / "file",
            "LOG_DIR": root / "log",
            "VAR_DIR": root / "var",
            "TMP_DIR": root / "tmp",
        }

        override_settings(**cls.temporary_directories)(cls)

        # override ansible secret (shouldn't be required after full DI change)

        override_settings(ANSIBLE_SECRET="verysecretstuff")(cls)

    @classmethod
    def setUpClass(cls):
        # important init for django is happening here
        super().setUpClass()

        # task runner "patch"
        cls.task_runner = get_task_runner_manager()

        # actually init temp directories
        for directory in cls.temporary_directories.values():
            directory.mkdir(exist_ok=True, parents=True)

        # ADCM setup is copied from previous base.py

        cls.test_bundles_dir = TEST_BUNDLES_DIR
        cls.test_files_dir = TEST_FILES_DIR

        init_roles()
        init()

    def setUp(self) -> None:
        super().setUp()

        # precaution to avoid getting launched task from previous test
        # YET it's still possible to get falsely "launched" with 200-ok -> 409 sort of combos
        # or 200 -> 200 gettings previously launched (thou unlikely)
        self.task_runner.reset()

        self.client.login(username="admin", password="admin")
