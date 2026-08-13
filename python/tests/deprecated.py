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

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from operator import itemgetter
from pathlib import Path
from typing import Any, TypeAlias
import tarfile

from api_v2.prototype.utils import accept_license
from audit.models import AuditLog, AuditObjectType, AuditSession
from cm.converters import orm_object_to_core_type
from cm.legacy.api import add_host_to_cluster, update_obj_config
from cm.legacy.services.bundle_alt.load import Directories, parse_bundle_archive
from cm.legacy.services.config import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from cm.legacy.services.job.action import prepare_task_for_action
from cm.legacy.services.mapping import set_host_component_mapping
from cm.legacy.utils import deep_merge
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    ADCMEntity,
    ADCMModel,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    JobLog,
    JobStatus,
    ObjectType,
    Prototype,
    Provider,
    Service,
    TaskLog,
)
from cm.transition.status import StatusScenarios
from core.action import Task
from core.action.job import TaskPayloadDTO
from core.legacy.cluster.types import HostComponentEntry
from core.legacy.rbac.dto import UserCreateDTO
from core.types import ActionTargetDescriptor, ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from infra.services import get_config_service
from rbac.models import Group, Policy, Role, RoleTypes, User
from rbac.scenarios import RBACScenarios
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.services.user import perform_user_creation
from use_cases.transition.cluster.create import (
    CreateCluster,
    CreateServicesFromPrototypes,
)
from use_cases.transition.hostprovider.create import create_host, create_hostprovider

APPLICATION_JSON = "application/json"

AuditTarget: TypeAlias = (
    Bundle | Cluster | Service | Component | ActionHostGroup | Provider | Host | User | Group | Role | Policy
)


class TestUserCreateDTO(UserCreateDTO):
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    is_superuser: bool = False

    password: str = ""


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


class BusinessLogicMixin(BundleLogicMixin):
    @staticmethod
    def add_cluster(bundle: Bundle, name: str, description: str = "") -> Cluster:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.CLUSTER).get()

        if prototype.license_path is not None:
            accept_license(prototype=prototype)
            prototype.refresh_from_db(fields=["license"])

        cluster_id = CreateCluster(config_service=get_config_service(), status_scenarios=StatusScenarios()).do(
            prototype=prototype, name=name, description=description
        )

        return Cluster.objects.get(id=cluster_id)

    @staticmethod
    def add_provider(bundle: Bundle, name: str, description: str = "") -> Provider:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.PROVIDER).first()
        provider_id = create_hostprovider(
            prototype=prototype,
            name=name,
            description=description,
            config_service=get_config_service(),
            status_scenarios=StatusScenarios(),
        )

        return Provider.objects.get(id=provider_id)

    def add_host(self, provider: Provider, fqdn: str, cluster: Cluster | None = None) -> Host:
        host_id = create_host(
            hostprovider=provider,
            name=fqdn,
            cluster=cluster,
            config_service=get_config_service(),
            rbac_scenarios=RBACScenarios(),
            status_scenarios=StatusScenarios(),
        )

        return Host.objects.get(id=host_id)

    @staticmethod
    def add_host_to_cluster(cluster: Cluster, host: Host) -> Host:
        return add_host_to_cluster(cluster=cluster, host=host, rbac_scenarios=RBACScenarios())

    @staticmethod
    def add_services_to_cluster(service_names: list[str], cluster: Cluster) -> QuerySet[Service]:
        service_prototypes = Prototype.objects.filter(
            type=ObjectType.SERVICE, name__in=service_names, bundle=cluster.prototype.bundle
        ).values_list("id", flat=True)
        services = CreateServicesFromPrototypes(
            config_service=get_config_service(),
            rbac_scenarios=RBACScenarios(),
            status_scenarios=StatusScenarios(),
        ).do(cluster=cluster, prototype_ids=list(service_prototypes))
        return Service.objects.filter(id__in=[service.id for service in services])

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
            target=ActionTargetDescriptor(id=target.id, type=target.type),
            orm_owner=owner,
            orm_target=host or owner,
            action=action.id,
            payload=payload or TaskPayloadDTO(),
            feature_scripts_jinja=feature_scripts_jinja,
        )

    def simulate_finished_task(self, object_: Cluster | Service | Component, action: Action) -> tuple[TaskLog, JobLog]:
        self.client.v2[object_, "actions", action, "run"].post(
            data={"configuration": None, "isVerbose": True, "hostComponentMap": [], "description": ""}
        )

        task_id = self.task_runner.expect_task_launched().id
        self.task_runner.run_task(task_id=task_id)

        task = TaskLog.objects.get(id=task_id)

        return task, task.joblog_set.last()

    def simulate_running_task(self, object_: Cluster | Service | Component, action: Action) -> tuple[TaskLog, JobLog]:
        self.client.v2[object_, "actions", action, "run"].post(
            data={"configuration": None, "isVerbose": True, "hostComponentMap": [], "description": ""}
        )

        task_id = self.task_runner.expect_task_launched().id
        self.task_runner.run_task(task_id)

        task = TaskLog.objects.get(id=task_id)
        job = task.joblog_set.last()

        task.status = JobStatus.RUNNING
        task.save(update_fields=["status"])

        job.status = JobStatus.RUNNING
        job.pid = 5_000_000
        job.save(update_fields=["status", "pid"])

        return task, job


class AuditMixin:
    def check_last_audit_record(
        self,
        model: type[AuditLog | AuditSession] = AuditLog,
        **kwargs,
    ) -> AuditLog:
        last_audit_record = model.objects.order_by("pk").last()
        self.assertIsNotNone(last_audit_record, f"{model.__name__} table is empty")

        # we always want to check who performed the audited action
        if model is AuditLog:
            kwargs.setdefault("user__username", "admin")

        # Object changes are {} for most cases, we always want to check it, but providing it each time is redundant.
        if model is AuditLog:
            kwargs.setdefault("object_changes", {})

        expected_record = model.objects.filter(**kwargs).order_by("pk").last()
        self.assertIsNotNone(expected_record, "Can't find audit record")
        self.assertEqual(last_audit_record.pk, expected_record.pk, "Expected audit record is not last")

        return last_audit_record

    @staticmethod
    def get_most_recent_audit_log() -> AuditLog | None:
        """Mostly for debug purposes"""
        return AuditLog.objects.order_by("pk").last()

    def prepare_audit_object_arguments(
        self,
        expected_object: AuditTarget | None,
        *,
        is_deleted: bool = False,
    ) -> dict[str, Any]:
        if expected_object is None:
            return {"audit_object__isnull": True}

        if isinstance(expected_object, ActionHostGroup):
            owner_name = self.prepare_audit_object_arguments(expected_object=expected_object.object)[
                "audit_object__object_name"
            ]
            name = f"{owner_name}/{expected_object.name}"
            type_ = AuditObjectType.ACTION_HOST_GROUP
        elif isinstance(expected_object, Component):
            name = (
                f"{expected_object.cluster.name}/{expected_object.service.display_name}/{expected_object.display_name}"
            )
            type_ = "component"
        elif isinstance(expected_object, Service):
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
            type_ = expected_object.__class__.__name__.lower()

        return {
            "audit_object__object_id": expected_object.pk,
            "audit_object__object_name": name,
            "audit_object__object_type": type_,
            "audit_object__is_deleted": is_deleted,
        }
