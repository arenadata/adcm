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

from dataclasses import dataclass, field
from operator import itemgetter
from pathlib import Path
from typing import Iterable
import tarfile

from api_v2.prototype.utils import accept_license
from cm.converters import orm_object_to_core_descriptor
from cm.legacy.api import add_host_to_cluster
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService, CreateDTO
from cm.legacy.services.mapping import set_host_component_mapping
from cm.models import (
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    Host,
    HostComponent,
    ObjectType,
    Prototype,
    Provider,
    Service,
)
from cm.transition.status import StatusScenarios
from core.config._service import ConfigService
from core.legacy.cluster.types import HostComponentEntry
from core.legacy.rbac.dto import UserCreateDTO
from core.settings import Directories
from faker import Faker
from rbac.models import User
from rbac.scenarios import RBACScenarios
from rbac.services.user import perform_user_creation
from use_cases.bundle import ParseBundleFromRequest
from use_cases.transition.cluster.create import CreateCluster, CreateServicesFromPrototypes
from use_cases.transition.hostprovider.create import create_host, create_hostprovider
import dishka


class TestUserCreateDTO(UserCreateDTO):
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    is_superuser: bool = False

    password: str = ""


@dataclass(slots=True)
class UseCases:
    container: dishka.Container
    faker: Faker = field(default_factory=Faker)

    def upload_bundle(self, src: Path) -> Bundle:
        with self.container() as container:
            directories = container.get(Directories)

            if src.is_dir():
                archive_path = prepare_bundle_file(source_dir=src, target_dir=directories.downloads)
            else:
                # for "easy" backward compatibility with "upload_and_load_bundle"
                # which accepted path to already packed archive
                archive_path = src

            uc = container.get(ParseBundleFromRequest)
            bundle_id = uc.do(archive=archive_path)

            return Bundle.objects.get(id=bundle_id)

    def add_cluster(self, bundle: Bundle, name: str | None = None, description: str = "") -> Cluster:
        prototype = Prototype.objects.filter(bundle=bundle, type=ObjectType.CLUSTER).get()

        if prototype.license_path is not None:
            accept_license(prototype=prototype)
            prototype.refresh_from_db(fields=["license"])

        with self.container() as container:
            uc = container.get(CreateCluster)

            cluster_id = uc.do(prototype=prototype, name=name or self.faker.name(), description=description)

        return Cluster.objects.get(id=cluster_id)

    def add_provider(self, bundle: Bundle, name: str | None = None, description: str = "") -> Provider:
        prototype = Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER)
        provider_id = create_hostprovider(
            prototype=prototype,
            name=name or self.faker.name(),
            description=description,
            config_service=self.container.get(ConfigService),
            status_scenarios=self.container.get(StatusScenarios),
        )

        return Provider.objects.get(id=provider_id)

    def add_host(self, provider: Provider, fqdn: str = "", name: str = "", cluster: Cluster | None = None) -> Host:
        name_ = name or fqdn
        if not name_:
            raise RuntimeError("Provide either fqdn or name")
        host_id = create_host(
            hostprovider=provider,
            name=name_,
            cluster=cluster,
            config_service=self.container.get(ConfigService),
            rbac_scenarios=self.container.get(RBACScenarios),
            status_scenarios=self.container.get(StatusScenarios),
        )

        return Host.objects.get(id=host_id)

    def add_host_to_cluster(self, cluster: Cluster, host: Host) -> Host:
        # todo use use case
        return add_host_to_cluster(cluster=cluster, host=host, rbac_scenarios=self.container.get(RBACScenarios))

    def add_services_to_cluster(self, names: list[str], cluster: Cluster) -> tuple[Service, ...]:
        service_prototypes = Prototype.objects.filter(
            type=ObjectType.SERVICE, name__in=names, bundle=cluster.prototype.bundle
        ).values_list("id", flat=True)

        with self.container() as container:
            uc = container.get(CreateServicesFromPrototypes)
            services = uc.do(cluster=cluster, prototype_ids=list(service_prototypes))

        return tuple(Service.objects.filter(id__in=(s.pk for s in services)))

    def set_hostcomponent(self, cluster: Cluster, entries: Iterable[tuple[Host, Component]]) -> list[HostComponent]:
        set_host_component_mapping(
            cluster_id=cluster.pk,
            bundle_id=cluster.bundle_id,
            new_mapping=(HostComponentEntry(host_id=host.pk, component_id=component.pk) for host, component in entries),
        )
        return list(HostComponent.objects.filter(cluster_id=cluster.pk))

    # todo add ahg_service to dependencies
    def create_action_host_group(
        self, name: str, owner: Cluster | Service | Component, description: str = ""
    ) -> ActionHostGroup:
        action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())
        return ActionHostGroup.objects.get(
            id=action_host_group_service.create(
                CreateDTO(
                    name=name,
                    owner=orm_object_to_core_descriptor(owner),
                    description=description,
                )
            )
        )

    # todo add ahg_service to dependencies
    def add_hosts_to_action_host_group(self, group_id: int, hosts: list[int]) -> None:
        action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())
        action_host_group_service.add_hosts_to_group(group_id=group_id, hosts=hosts)

    # RBAC

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


# Utilities


def prepare_bundle_file(source_dir: Path, target_dir: Path) -> Path:
    bundle_file = target_dir / f"{source_dir.name}.tar"

    with tarfile.open(target_dir / bundle_file, "w") as tar:
        for file in source_dir.iterdir():
            tar.add(name=file, arcname=file.name)

    return bundle_file
