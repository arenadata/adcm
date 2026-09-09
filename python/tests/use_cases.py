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
from dataclasses import dataclass, field
from operator import itemgetter
from pathlib import Path
import tarfile

from cm.converters import orm_object_to_core_descriptor
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService, CreateDTO
from cm.legacy.services.cluster import perform_host_to_cluster_map
from cm.legacy.services.config import convert_attr_to_adcm_meta
from cm.legacy.services.mapping import set_host_component_mapping
from cm.legacy.utils import deep_merge
from cm.models import (
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    MainObject,
    ObjectType,
    Prototype,
    Provider,
    Service,
)
from cm.transition.status import StatusScenarios
from core.cluster import ClusterService
from core.config import ConfigService, Configuration, ConfigurationExtraInfo
from core.config._types import Attributes
from core.legacy.cluster.types import HostComponentEntry
from core.legacy.rbac.dto import UserCreateDTO
from core.settings import Directories
from core.types import ADCMHostGroupType, Descriptor
from django.contrib.contenttypes.models import ContentType
from faker import Faker
from rbac.models import Group, User
from rbac.scenarios import RBACScenarios
from rbac.services.group import create as create_group
from rbac.services.user import perform_user_creation
from use_cases.bundle import AcceptLicense, ParseBundleFromRequest
from use_cases.transition.cluster.create import CreateCluster, CreateServicesFromPrototypes
from use_cases.transition.config import UpdateConfigurationOfHostGroup, UpdateConfigurationOfObject
from use_cases.transition.hostprovider.create import CreateHost, CreateHostprovider
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
            self.accept_license(prototype)

        with self.container() as container:
            uc = container.get(CreateCluster)

            cluster_id = uc.do(prototype=prototype, name=name or self.faker.name(), description=description)

        return Cluster.objects.get(id=cluster_id)

    def add_provider(self, bundle: Bundle, name: str | None = None, description: str = "") -> Provider:
        prototype = Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER)

        with self.container() as container:
            uc = container.get(CreateHostprovider)
            provider_id = uc.do(prototype=prototype, name=name or self.faker.name(), description=description)

        return Provider.objects.get(id=provider_id)

    def add_host(self, provider: Provider, fqdn: str = "", name: str = "", cluster: Cluster | None = None) -> Host:
        name_ = name or fqdn
        if not name_:
            raise RuntimeError("Provide either fqdn or name")

        with self.container() as container:
            uc = container.get(CreateHost)
            host_id = uc.do(hostprovider=provider, name=name_, cluster=cluster)

        return Host.objects.get(id=host_id)

    def add_host_to_cluster(self, cluster: Cluster, host: Host) -> Host:
        perform_host_to_cluster_map(
            cluster_id=cluster.pk,
            hosts=[host.pk],
            status_service=self.container.get(StatusScenarios),
            rbac_scenarios=self.container.get(RBACScenarios),
        )
        # `perform_host_to_cluster_map` updates the DB without touching the passed-in ORM instance,
        # unlike the old `add_host_to_cluster` it replaces — refresh it in place so callers that don't
        # capture the return value (many don't) still see `host.cluster` populated.
        host.refresh_from_db(fields=["cluster"])

        return host

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
            cluster_service=self.container.get(ClusterService),
        )
        return list(HostComponent.objects.filter(cluster_id=cluster.pk))

    def add_config_host_group(
        self, owner: Cluster | Service | Component | Provider, name: str, description: str = ""
    ) -> ConfigHostGroup:
        host_group = ConfigHostGroup.objects.create(
            object_type=ContentType.objects.get_for_model(model=owner),
            object_id=owner.pk,
            name=name,
            description=description,
        )
        self.container.get(ConfigService).create_initial_configuration_of_host_group(
            group=Descriptor(id=host_group.pk, type=ADCMHostGroupType.CONFIG),
            owner=orm_object_to_core_descriptor(owner),
        )
        host_group.refresh_from_db(fields=("config",))

        return host_group

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

    def change_config(
        self,
        owner: MainObject | ConfigHostGroup,
        values_diff: dict | None = None,
        meta_diff: dict | None = None,
        preprocess_config: Callable[[dict], dict] = lambda x: x,
    ) -> None:
        owner.refresh_from_db(fields=["config"])
        current_config = ConfigLog.objects.get(id=owner.config.current)

        values = deep_merge(origin=preprocess_config(current_config.config), renovator=values_diff or {})
        attr = {
            key: Attributes(is_active=entry.get("isActive"), is_synced=entry.get("isSynchronized"))
            for key, entry in deep_merge(
                origin=convert_attr_to_adcm_meta(current_config.attr), renovator=meta_diff or {}
            ).items()
        }

        config = Configuration(values=values, attributes=attr)

        if isinstance(owner, ConfigHostGroup):
            self.set_config_of_group(group=owner, config=config)
        else:
            self.set_config(owner=owner, config=config)

        owner.refresh_from_db(fields=["config"])

    def set_config(self, owner: MainObject, config: Configuration) -> None:
        with self.container() as container:
            uc = container.get(UpdateConfigurationOfObject)
            uc.do(
                owner=owner,
                input_config=config,
                convert=lambda x, _: x,
                config_extra_info=ConfigurationExtraInfo(description="", created_by="system"),
            )

    def set_config_of_group(self, group: ConfigHostGroup, config: Configuration) -> None:
        owner = group.object

        with self.container() as container:
            uc = container.get(UpdateConfigurationOfHostGroup)
            uc.do(
                owner=owner,
                input_config=config,
                convert=lambda x, _: x,
                config_extra_info=ConfigurationExtraInfo(description="", created_by="system"),
                group=group,
            )

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

    def create_group(self, display_name: str, users: Iterable[int] | None = None, description: str = "") -> Group:
        return create_group(
            name_to_display=display_name, description=description, user_set=[{"id": id_} for id_ in users or []]
        )

    def set_unsupported_contract_version(self, prototype: Prototype, contract_version: str = "0.999") -> None:
        Bundle.objects.filter(pk=prototype.bundle_id).update(contract_version=contract_version)

    def accept_license(self, prototype: Prototype) -> None:
        with self.container() as container:
            accept_license = container.get(AcceptLicense)
            accept_license.do(prototype=prototype)

        prototype.refresh_from_db(fields=["license"])


# Utilities


def prepare_bundle_file(source_dir: Path, target_dir: Path) -> Path:
    bundle_file = target_dir / f"{source_dir.name}.tar"

    with tarfile.open(target_dir / bundle_file, "w") as tar:
        for file in source_dir.iterdir():
            tar.add(name=file, arcname=file.name)

    return bundle_file
