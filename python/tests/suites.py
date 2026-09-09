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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Final, Literal, TypeVar
import json
import datetime

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
)
from api_v2.tests.helpers import create_bundle_and_prototype_rows
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
    AuditUser,
)
from cm.converters import core_type_to_model, orm_object_to_core_descriptor
from cm.impl.job.repo import JobRepo, _get_selector_for_core_object
from cm.legacy.services.job.run.target_factories import prepare_ansible_job_config
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Bundle,
    Cluster,
    Component,
    ConfigLog,
    Host,
    JobLog,
    ObjectType,
    ProductCategory,
    Provider,
    Service,
    SignatureStatus,
    TaskLog,
)
from core.action import Job
from core.config import ConfigService
from core.legacy.job.executors import Executor as JobExecutor
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.utils import timezone
from init_db import init
from rbac.models import Group, OriginType, Policy, PolicyObject, Role, User
from rbac.upgrade.role import init_roles
from rest_framework.status import HTTP_200_OK
from unittest_parametrize import ParametrizedTestCase
import yaml
import dishka
import django.test

from tests._base import WithIndependentDirectories
from tests.client import ADCMTestClient, APINode
from tests.dependencies import (
    RBACScenariosOverride,
    get_container_manager,
    get_default_overridden_providers,
    get_status_scenarios_manager,
)
from tests.deprecated import AuditMixin, BusinessLogicMixin, TaskTestMixin
from tests.task_flow import TaskFlowMixin
from tests.use_cases import UseCases
from tests.utils import calculate_time_with_delta, extract_from_nested_structure

PROJECT_DIR = Path(__file__).parent.parent.parent
TEST_API_V2_BUNDLES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "bundles"
TEST_API_V2_FILES_DIR = PROJECT_DIR / "python" / "api_v2" / "tests" / "files"
TEST_ANSIBLE_PLUGINS_BUNDLES_DIR = PROJECT_DIR / "python" / "ansible_plugin" / "tests" / "bundles"


@dataclass(slots=True)
class SuiteSetup:
    environment: Literal["minimal", "with-rbac"] = "minimal"


SETUP_MINIMAL: Final = SuiteSetup(environment="minimal")
SETUP_WITH_RBAC: Final = SuiteSetup(environment="with-rbac")


class _ADCMTestCase(TaskFlowMixin, django.test.SimpleTestCase, WithIndependentDirectories):
    suite_setup: SuiteSetup = SETUP_MINIMAL

    base_dir = Path(__file__).parent.parent.parent

    @classmethod
    def setUpClass(cls) -> None:
        cls._create_directories_on_fs()
        cls._clean_directories()

        cls._prepare_environment()
        cls.container = get_container_manager().container

        cls.uc = UseCases(container=cls.container)

        super().setUpClass()

    def setUp(self) -> None:
        super().setUp()

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


class GenericTestCase(_ADCMTestCase, django.test.TestCase):
    ...


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

                repo = JobRepo()

                context = prepare_ansible_job_config(
                    task=repo.get_task(id=task_id),
                    job=repo.get_job(id=job_id),
                    configuration=configuration,
                    config_service=container.get(ConfigService),
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

    def get_task_jobs(self, task_id):
        return JobRepo().get_task_jobs(task_id)


class ADCMDjangoAPISuite(ParametrizedTestCase, _ADCMTestCase, AuditMixin, BusinessLogicMixin, django.test.TestCase):
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
        cls.bundle_hp_1 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_1")
        cls.bundle_hp_2 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_2")
        cls.bundle_hp_3 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_3")
        cls.set_bundle_signature_status(cls.bundle_cl_1, SignatureStatus.VALID)

        # prepare clusters
        cls.cl_1 = cls.uc.add_cluster(cls.bundle_cl_1, "AlphaCl")
        cls.cl_2 = cls.uc.add_cluster(cls.bundle_cl_2, "BettaCl")
        cls.cl_3 = cls.uc.add_cluster(cls.bundle_cl_3, "GammaCl")
        cls.set_state(cls.cl_1, "installed")

        # prepare data for check contract versions
        cls.unsupported_version = "0.999"
        cls.supported_bundle_count = 6
        cls.unsupported_bundle, cls.unsupported_prototype = create_bundle_and_prototype_rows(
            [
                {
                    "contract_version": cls.unsupported_version,
                    "name": "unsupported_bundle",
                    "display_name": "Unsupported Cluster",
                    "version": "1.0.0",
                    "obj_type": ObjectType.CLUSTER,
                }
            ]
        )[0]

        # prepare service with components
        cls.service_1, *_ = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cl_1)
        # prepare components
        components = cls.get_components(cls.service_1)
        cls.comp_1, cls.comp_2, cls.comp_3 = components[0], components[1], components[2]

        # prepare other services
        cls.service_2, cls.service_3 = cls.uc.add_services_to_cluster(
            names=["service_2", "service_3"], cluster=cls.cl_1
        )
        cls.set_state(cls.service_3, "installed")

        # prepare hostproviders
        cls.hp_1 = cls.uc.add_provider(cls.bundle_hp_1, "FooProvider")
        cls.hp_2 = cls.uc.add_provider(cls.bundle_hp_2, "BarProvider")
        cls.hp_3 = cls.uc.add_provider(cls.bundle_hp_3, "FizzProvider")
        cls.set_state(cls.hp_1, "installed")

        # prepare hosts
        cls.host_1 = cls.uc.add_host(provider=cls.hp_1, fqdn="Host1", cluster=cls.cl_1)
        cls.host_2 = cls.uc.add_host(provider=cls.hp_2, fqdn="Host2", cluster=cls.cl_1)
        cls.host_3 = cls.uc.add_host(provider=cls.hp_2, fqdn="Host3", cluster=cls.cl_3)
        cls.host_4 = cls.uc.add_host(provider=cls.hp_3, fqdn="Host4")
        cls.set_state(cls.host_2, "installed")

        # host-component mapping
        cls.uc.set_hostcomponent(cluster=cls.cl_1, entries=[(cls.host_1, cls.comp_1), (cls.host_2, cls.comp_2)])

        # prepare tasks
        cls.task_cl_1 = cls.create_task(
            owner=cls.cl_1, action_name="check_action", name="a_task", display_name="A task", duration=4
        )
        cls.task_service_1 = cls.create_task(
            owner=cls.service_1,
            action_name="check_action",
            name="b_task",
            display_name="B task",
            duration=3,
            status="success",
        )
        cls.task_hp_1 = cls.create_task(
            owner=cls.hp_1, action_name="provider_action", name="c_task", display_name="C task", duration=2
        )

        # prepare audit users and objects
        cls.cluster_admin = cls.uc.create_user(
            user_data={"username": "AdminClusterBobby", "password": "admin_password"}
        )
        cls.provider_admin = cls.uc.create_user(
            user_data={"username": "ProviderAdminPeter", "password": "admin_password"}
        )

        cls.cluster_audit_admin = cls.get_audit_user("AdminClusterBobby")
        cls.provider_audit_admin = cls.get_audit_user("ProviderAdminPeter")
        cls.non_existent_user_name = "Invisible"

        cls.audit_obj_cluster = cls.create_audit_obj(entity=cls.cl_1, object_type=AuditObjectType.CLUSTER)
        cls.audit_obj_service = cls.create_audit_obj(entity=cls.service_1, object_type=AuditObjectType.SERVICE)
        cls.audit_obj_provider = cls.create_audit_obj(entity=cls.hp_1, object_type=AuditObjectType.PROVIDER)

        # prepare audit log records
        now_time = timezone.now()
        cls.audit_log_time_1 = calculate_time_with_delta(delta_value=20, base_time=now_time)
        cls.audit_log_time_2 = calculate_time_with_delta(delta_value=10, base_time=now_time)
        cls.audit_log_time_3 = calculate_time_with_delta(delta_value=5, base_time=now_time)

        cls.matched_time_from_value = calculate_time_with_delta(delta_value=10, base_time=now_time, isoformat=True)
        cls.empty_match_time_from_value = calculate_time_with_delta(delta_value=1, base_time=now_time, isoformat=True)
        cls.matched_time_to_value = calculate_time_with_delta(delta_value=20, base_time=now_time, isoformat=True)
        cls.empty_match_time_to_value = calculate_time_with_delta(delta_value=25, base_time=now_time, isoformat=True)
        cls.audit_log_update_service = cls.create_audit_operation_log(
            audit_object=cls.audit_obj_service,
            operation_name="update_service",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=cls.cluster_audit_admin,
            operation_time=cls.audit_log_time_2,
        )
        cls.audit_log_create_provider_fail = cls.create_audit_operation_log(
            audit_object=cls.audit_obj_provider,
            operation_name="create_provider",
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=cls.provider_audit_admin,
            operation_time=cls.audit_log_time_3,
        )
        cls.audit_log_create_cluster = cls.create_audit_operation_log(
            audit_object=cls.audit_obj_cluster,
            operation_name="create_cluster",
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=cls.cluster_audit_admin,
            operation_time=cls.audit_log_time_1,
        )
        cls.audit_login_wrong_password = cls.create_audit_login_log(
            user=cls.provider_audit_admin,
            login_result=AuditSessionLoginResult.WRONG_PASSWORD,
            login_time=cls.audit_log_time_2,
            login_details={"username": cls.provider_audit_admin.username},
        )
        cls.audit_login_user_not_found = cls.create_audit_login_log(
            user=None,
            login_result=AuditSessionLoginResult.USER_NOT_FOUND,
            login_time=cls.audit_log_time_3,
            login_details={"username": cls.non_existent_user_name},
        )
        cls.audit_login_success_cluster = cls.create_audit_login_log(
            user=cls.cluster_audit_admin,
            login_result=AuditSessionLoginResult.SUCCESS,
            login_time=cls.audit_log_time_1,
            login_details={"username": cls.cluster_audit_admin.username},
        )

        # prepare users
        assert User.objects.filter(username="admin").exists(), 'The user "admin" is expected to exist'  # noqa: S101
        group = cls.uc.create_group(display_name="Group1")
        username = "TestUser1"
        cls.uc.create_user(
            username=username,
            password=username * 2,
            email=f"{username.lower()}@example.com",
            groups=[{"id": group.id}],
        )
        User.objects.filter(username=username).update(type=OriginType.LDAP.value, blocked_at=timezone.now())

        # prepare groups
        admin = User.objects.get(username="admin")
        group2 = cls.uc.create_group(display_name="TestGroup", users=[admin.pk])
        ldap_group = cls.uc.create_group(display_name="LDAPTestGroup")
        ldap_group.type = OriginType.LDAP.value
        ldap_group.save(update_fields=["type"])

        # prepare roles
        category = ProductCategory.objects.create(value="TestCategory")
        custom_role = Role.objects.create(
            name="CustomRole",
            display_name="CustomRole",
            module_name=".",
            class_name=".",
        )
        custom_role.category.add(category)
        Role.objects.create(
            name="CustomRoleAnyCategory",
            display_name="CustomRoleAnyCategory",
            module_name=".",
            class_name=".",
            any_category=True,
        )

        # prepare policies
        cls.policy = cls.create_policy(name="CustomPolicy", role=custom_role, group=group)
        cluster_role = Role.objects.get(display_name="Add hosts to the Cluster")
        cls.create_policy(name="ClusterPolicy", role=cluster_role, group=group2, obj=cls.cl_1)
        service_role = Role.objects.get(display_name="View service config")
        cls.create_policy(name="ServicePolicy", role=service_role, group=group2, obj=cls.service_1)

    def setUp(self) -> None:
        super().setUp()

        self.client.login(username="admin", password="admin")

    def get_r(self, url: APINode, query: dict) -> dict:
        response = url.get(query=query)
        self.assertEqual(response.status_code, HTTP_200_OK)
        return response.json()

    def get_results(self, url: APINode, value_path: str, query: dict) -> list:
        response = self.get_r(url=url, query=query)
        nested_data = response if isinstance(response, list) else response["results"]
        return extract_from_nested_structure(nested_data, value_path)

    @staticmethod
    def set_state(entity: ADCMEntity, state: str) -> None:
        entity.set_state(state)

    @staticmethod
    def set_bundle_signature_status(bundle: Bundle, status: SignatureStatus) -> None:
        Bundle.objects.filter(pk=bundle.pk).update(signature_status=status)

    @staticmethod
    def get_components(service: Service) -> QuerySet[Component]:
        return Component.objects.filter(service=service).order_by("pk")

    @staticmethod
    def create_task(
        owner: Cluster | Service | Component | Provider | Host,
        action_name: str,
        name: str,
        display_name: str,
        duration: int,
        status: str | None = None,
    ) -> TaskLog:
        action = Action.objects.get(name=action_name, prototype=owner.prototype)

        owner_descr = orm_object_to_core_descriptor(owner)

        # to get the selector need to use temporarily the protected function
        selector = _get_selector_for_core_object(target=owner_descr, owner=owner_descr)
        object_type = core_type_to_model(core_type=owner_descr.type).class_content_type

        task = TaskLog.objects.create(
            action=action,
            object_id=owner_descr.id,
            object_type=object_type,
            owner_id=owner_descr.id,
            owner_type=owner_descr.type.value,
            verbose=False,
            status=status if status else "created",
            selector=selector,
            is_blocking=True,
            name=name,
            display_name=display_name,
            description="",
        )

        task.start_date = timezone.now() - timedelta(seconds=duration)
        task.finish_date = timezone.now()
        task.save()
        return task

    @staticmethod
    def get_audit_user(username: str) -> AuditUser:
        return AuditUser.objects.filter(username=username).order_by("-pk").first()

    @staticmethod
    def create_audit_obj(entity: ADCMEntity, object_type: AuditObjectType) -> AuditObject:
        return AuditObject.objects.create(
            object_id=entity.pk,
            object_name=entity.name,
            object_type=object_type,
        )

    @staticmethod
    def create_audit_operation_log(
        audit_object: AuditObject,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: AuditUser,
        operation_time: datetime.datetime,
    ) -> AuditLog:
        audit_log = AuditLog.objects.create(
            audit_object=audit_object,
            operation_name=operation_name,
            operation_type=operation_type,
            operation_result=operation_result,
            user=user,
        )
        audit_log.operation_time = operation_time
        audit_log.save()
        return audit_log

    @staticmethod
    def create_audit_login_log(
        login_result: AuditSessionLoginResult,
        login_time: datetime.datetime,
        login_details: dict,
        user: AuditUser | None = None,
    ) -> AuditSession:
        audit_session = AuditSession.objects.create(
            user=user,
            login_result=login_result,
            login_details=login_details,
        )
        audit_session.login_time = login_time
        audit_session.save()
        return audit_session

    @staticmethod
    def create_policy(name: str, role: Role, group: Group, obj: Cluster | Service | None = None) -> Policy:
        policy = Policy.objects.create(name=name, description="", role=role)
        policy.group.add(group)

        if obj:
            content_type = ContentType.objects.get_for_model(obj)
            policy_object, _ = PolicyObject.objects.get_or_create(object_id=obj.id, content_type=content_type)
            policy.object.add(policy_object)

        return policy
