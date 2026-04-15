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

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ConfigLog,
    SignatureStatus,
)
from infra.services import prepare_container
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.status import HTTP_200_OK
import dishka
import django.test

from tests._base import WithIndependentDirectories
from tests.client import ADCMTestClient, APINode
from tests.dependencies import (
    RBACScenariosOverride,
    get_container_manager,
    get_default_overridden_providers,
    get_status_scenarios_manager,
    get_task_runner_manager,
)
from tests.deprecated import AuditMixin, BusinessLogicMixin
from tests.use_cases import UseCases

PROJECT_DIR = Path(__file__).parent.parent.parent
TEST_API_V2_BUNDLES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "bundles"
TEST_API_V2_FILES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "files"


@dataclass(slots=True)
class SuiteSetup:
    environment: Literal["minimal", "with-rbac"] = "minimal"


SETUP_MINIMAL: Final = SuiteSetup(environment="minimal")
SETUP_WITH_RBAC: Final = SuiteSetup(environment="with-rbac")


class _ADCMTestCase(django.test.SimpleTestCase, WithIndependentDirectories):
    suite_setup: SuiteSetup = SETUP_MINIMAL

    base_dir = Path(__file__).parent.parent.parent

    @classmethod
    def setUpClass(cls) -> None:
        cls._create_directories_on_fs()
        cls._clean_directories()

        cls._prepare_environment()
        cls.container = get_container_manager().container

        cls.uc = UseCases(container=cls.container)
        cls.task_runner = get_task_runner_manager()

        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()

        self.task_runner.reset()
        get_status_scenarios_manager().reset()

    @classmethod
    def _prepare_environment(cls) -> None:
        container_manager = get_container_manager()
        container_environment_name = cls.suite_setup.environment

        if container_environment_name not in container_manager.containers:
            match container_environment_name:
                case "minimal":
                    providers = get_default_overridden_providers()

                case "with-rbac":
                    providers = [
                        provider
                        for provider in get_default_overridden_providers()
                        if not isinstance(provider, RBACScenariosOverride)
                    ]

            container = dishka.make_container(*providers)
            container_manager.containers[container_environment_name] = container

        container_manager.current = container_environment_name

        # TODO: ADCM-7513
        prepare_container.cache_clear()

    @classmethod
    def _initialize_roles_and_adcm(cls) -> None:
        init_roles()
        init(container=cls.container)

    @classmethod
    def _set_adcm_max_password_length(cls) -> None:
        config_id = ADCM.objects.values_list("config__current", flat=True).get()

        config_log = ConfigLog.objects.get(id=config_id)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])


class ADCMDjangoAPISuite(_ADCMTestCase, AuditMixin, BusinessLogicMixin, django.test.TestCase):
    # is required for correct type detection in test cases
    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient

    # strange to bind it in here, but api cases will be related to `api_v2` for a while
    test_bundles_dir = TEST_API_V2_BUNDLES_DIR
    test_files_dir = TEST_API_V2_FILES_DIR

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()
        cls._set_adcm_max_password_length()

        cluster_bundle_1_path = cls.test_bundles_dir / "cluster_one"
        cluster_bundle_2_path = cls.test_bundles_dir / "cluster_two"
        provider_bundle_path = cls.test_bundles_dir / "provider"

        cls.bundle_1 = cls.uc.upload_bundle(src=cluster_bundle_1_path)
        cls.bundle_2 = cls.uc.upload_bundle(src=cluster_bundle_2_path)
        cls.provider_bundle = cls.uc.upload_bundle(src=provider_bundle_path)

        cls.cluster_1 = cls.uc.add_cluster(bundle=cls.bundle_1, name="cluster_1", description="cluster_1")
        cls.cluster_2 = cls.uc.add_cluster(bundle=cls.bundle_2, name="cluster_2", description="cluster_2")
        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="provider", description="provider")

    def setUp(self) -> None:
        super().setUp()

        self.client.login(username="admin", password="admin")


class ADCMFiltersDataSuite(_ADCMTestCase, django.test.TestCase):
    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient
    test_bundles_dir = TEST_API_V2_BUNDLES_DIR / "filtering"

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        # prepare bundles
        cls.bundle_cl_1 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_1")
        cls.bundle_cl_2 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_2")
        cls.bundle_cl_3 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_3")

        # prepare clusters
        cls.cl_1 = cls.uc.add_cluster(cls.bundle_cl_1, "cluster_1")
        cls.cl_2 = cls.uc.add_cluster(cls.bundle_cl_2, "cluster_2")
        cls.cl_3 = cls.uc.add_cluster(cls.bundle_cl_3, "cluster_3")

    def setUp(self) -> None:
        super().setUp()

        self.client.login(username="admin", password="admin")

    def get_r(self, url: APINode, query: dict) -> dict:
        response = url.get(query=query)
        self.assertEqual(response.status_code, HTTP_200_OK)
        return response.json()

    def extract_values(self, data: dict, value_path: str) -> list:
        """
        Extract values along a path from a nested structure.
        """

        keys = value_path.split(".")
        values = []
        for item in data:
            current = item
            for key in keys:
                current = current[key]
            values.append(current)
        return values

    def get_results(self, url: APINode, value_path: str, query: dict) -> list:
        response = self.get_r(url=url, query=query)
        return self.extract_values(response["results"], value_path)

    def set_cluster_state(self, cluster: Cluster, state: str) -> None:
        cluster.set_state(state)

    def normalize_upload_time(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def set_bundle_signature_status(self, bundle: Bundle, status: SignatureStatus) -> None:
        Bundle.objects.filter(pk=bundle.pk).update(signature_status=status)
