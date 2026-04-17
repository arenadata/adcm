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
from pathlib import Path
from typing import Any, Callable, Final, Literal, TypeVar
import json

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
)
from cm.legacy.services.job.run._target_factories import prepare_ansible_job_config
from cm.legacy.services.job.run.repo import JobRepoImpl
from cm.models import (
    ADCM,
    ConfigLog,
    JobLog,
)
from core.legacy.job.executors import Executor as JobExecutor
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.legacy.job.types import Job
from django.conf import settings
from infra.services import prepare_container
from init_db import init
from rbac.upgrade.role import init_roles
import yaml
import dishka
import django.test

from tests._base import WithIndependentDirectories
from tests.client import ADCMTestClient
from tests.dependencies import (
    RBACScenariosOverride,
    get_container_manager,
    get_default_overridden_providers,
    get_status_scenarios_manager,
    get_task_runner_manager,
)
from tests.deprecated import AuditMixin, BusinessLogicMixin, TaskTestMixin
from tests.use_cases import UseCases

PROJECT_DIR = Path(__file__).parent.parent.parent
TEST_API_V2_BUNDLES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "bundles"
TEST_API_V2_FILES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "files"
TEST_ANSIBLE_PLUGINS_BUNDLES_DIR = PROJECT_DIR / "python" / "ansible_plugin" / "tests" / "bundles"


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


Executor = TypeVar("Executor", bound=ADCMAnsiblePluginExecutor)


class ADCMPluginExecutorSuite(
    _ADCMTestCase,
    BusinessLogicMixin,
    TaskTestMixin,
    django.test.TestCase,
):
    bundles_dir = TEST_ANSIBLE_PLUGINS_BUNDLES_DIR

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        cls.cluster_bundle = cls.uc.upload_bundle(cls.bundles_dir / "cluster")
        cls.provider_bundle = cls.uc.upload_bundle(cls.bundles_dir / "provider")

        cls.cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="Just Cluster")

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Just HP")
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host-1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host-2")

    def prepare_executor(
        self, executor_type: type[Executor], call_arguments: dict | str, call_context: dict | JobLog | Job | int
    ) -> Executor:
        """
        Prepare plugin executor more or less like it will be created inside Ansible plugin call

        You can specify `call_arguments` as dict, then it'll be passed right into executor's init function
        or write it as plain yaml string (that'll be evaluated to dict) to "imitate" ansible plugin call description
        (note that it should be inner section of plugin (without name).
        If it is a string, it'll be parsed with `yaml` (so no ansible filters or environment will be there).

        `call_context` can be either a context dict (with `type` and `*_id` fields)
        or a job (`Job`, `JobLog` or job's id as `int`) based on which this function will build context.
        """
        with self.container(scope=dishka.Scope.REQUEST) as container:
            arguments = call_arguments
            if isinstance(arguments, str):
                arguments = yaml.safe_load(arguments)

            context = call_context
            if not isinstance(call_context, dict):
                configuration = ExternalSettings(
                    adcm=ADCMSettings(
                        code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR
                    ),
                    ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
                    integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
                    consul=ConsulSettings(
                        url=settings.CONSUL_URL,
                        datacenter=settings.CONSUL_DATACENTER,
                        cacert_file=settings.CONSUL_CACERT_FILE,
                    ),
                )

                job_id = call_context if isinstance(call_context, int) else call_context.id
                task_id = JobLog.objects.values_list("task_id", flat=True).get(id=job_id)

                context = prepare_ansible_job_config(
                    task=JobRepoImpl.get_task(id=task_id),
                    job=JobRepoImpl.get_job(id=job_id),
                    configuration=configuration,
                )

            return executor_type(arguments=arguments, runtime_vars=context, container=container)

    def build_executor_call(
        self,
        arguments: dict | str,
        executor_type: type[ADCMAnsiblePluginExecutor],
    ) -> Callable[[JobExecutor], Any]:
        def _executor_func(executor: JobExecutor) -> int:
            context = json.loads((executor._config.work_dir / "config.json").read_text())["context"]
            plugin_executor = self.prepare_executor(
                executor_type=executor_type, call_arguments=arguments, call_context=context
            )
            result = plugin_executor.execute()
            return 0 if result.error is None else 1

        return _executor_func


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
