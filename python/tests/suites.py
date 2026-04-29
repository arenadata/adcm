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
from datetime import timedelta
from pathlib import Path
from typing import Final, Literal
import datetime

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
from cm.impl.job.repo import _get_selector_for_core_object
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Bundle,
    Cluster,
    Component,
    ConfigLog,
    Host,
    Provider,
    Service,
    SignatureStatus,
    TaskLog,
)
from django.db.models import QuerySet
from django.utils import timezone
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
from tests.utils import calculate_time_with_delta, extract_from_nested_structure

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
        cls.bundle_hp_1 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_1")
        cls.bundle_hp_2 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_2")
        cls.bundle_hp_3 = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider_3")
        cls.set_bundle_signature_status(cls.bundle_cl_1, SignatureStatus.VALID)

        # prepare clusters
        cls.cl_1 = cls.uc.add_cluster(cls.bundle_cl_1, "AlphaCl")
        cls.cl_2 = cls.uc.add_cluster(cls.bundle_cl_2, "BettaCl")
        cls.cl_3 = cls.uc.add_cluster(cls.bundle_cl_3, "GammaCl")
        cls.set_state(cls.cl_1, "installed")

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

    def setUp(self) -> None:
        super().setUp()

        self.client.login(username="admin", password="admin")

    def get_r(self, url: APINode, query: dict) -> dict:
        response = url.get(query=query)
        self.assertEqual(response.status_code, HTTP_200_OK)
        return response.json()

    def get_results(self, url: APINode, value_path: str, query: dict) -> list:
        response = self.get_r(url=url, query=query)
        return extract_from_nested_structure(response["results"], value_path)

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
