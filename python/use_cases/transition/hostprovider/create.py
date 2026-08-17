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

from cm import converters
from cm.errors import AdcmEx
from cm.legacy.api import check_license
from cm.legacy.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.legacy.services.concern._operations import create_issue
from cm.legacy.services.concern.cases import recalculate_own_concerns_on_add_hosts
from cm.legacy.services.concern.checks import object_configuration_has_issue
from cm.legacy.services.concern.distribution import (
    distribute_concern_from_provider_to_host,
    distribute_concern_on_related_objects,
)
from cm.models import Cluster, ConcernCause, Host, Prototype, Provider
from cm.transition.concern import create_and_distribute_hostcomponent_concern_on_add_host_to_cluster
from cm.transition.status import StatusScenarios
from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, ProviderID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios
import core


@dataclass(slots=True)
class CreateHostprovider:
    config_service: core.config.ConfigService
    status_scenarios: StatusScenarios
    available_contract_versions: core.bundle.AvailableContractVersions

    @convert_bundle_errors_to_adcm_ex
    def do(self, prototype: Prototype, name: str, description: str) -> ProviderID:
        if prototype.type != ADCMCoreType.PROVIDER.value:
            raise AdcmEx("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {prototype.type}")

        core.bundle.check_contract_version_supported(
            current_version=prototype.bundle.contract_version,
            available_contract_versions=self.available_contract_versions,
        )

        check_license(prototype)

        with atomic():
            provider = _create_provider(
                prototype=prototype, name=name, description=description, config_service=self.config_service
            )

            provider_cod = converters.orm_object_to_core_descriptor(provider)
            concern_id = None
            related_objects = {}
            if object_configuration_has_issue(provider):
                concern = create_issue(owner=provider_cod, cause=ConcernCause.CONFIG)
                concern_id = concern.pk
                related_objects = distribute_concern_on_related_objects(owner=provider_cod, concern_id=concern_id)

        if concern_id:
            self.status_scenarios.notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

        return provider.pk


def create_host(
    hostprovider: Provider,
    name: str,
    cluster: Cluster | None,
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> HostID:
    with atomic():
        bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=hostprovider.prototype_id)  # pyright: ignore [reportAttributeAccessIssue]
        host_prototype = Prototype.objects.get(type=ADCMCoreType.HOST.value, bundle_id=bundle_id)

        check_license(prototype=host_prototype)

        host = Host.objects.create(prototype=host_prototype, provider_id=hostprovider.pk, fqdn=name, cluster=cluster)
        descriptor = CoreObjectDescriptor(id=host.pk, type=ADCMCoreType.HOST)
        config_service.create_initial_configuration_if_required(owner=descriptor)

        cluster = host.cluster
        # Calculate concerns
        ## calculate host concerns (config)
        concern_map = {ADCMCoreType.HOST: {host.pk: set()}}
        host_concern_map = recalculate_own_concerns_on_add_hosts(host=host)

        if host_concern_map:
            concern_id = next(iter(host_concern_map[ADCMCoreType.HOST][host.pk]))
            host.concerns.add(concern_id)
            concern_map[ADCMCoreType.HOST][host.pk].add(concern_id)

        ## distribute concerns to host from provider
        attached_concern_map = distribute_concern_from_provider_to_host(host_id=host.pk)

        if attached_concern_map:
            concern_map[ADCMCoreType.HOST][host.pk] |= attached_concern_map[ADCMCoreType.HOST][host.pk]

        concern_id = None
        related_objects = {}

        if cluster is not None:
            concern_id, related_objects = create_and_distribute_hostcomponent_concern_on_add_host_to_cluster(
                cluster=cluster
            )

        # Re apply policies
        rbac_scenarios.re_apply_object_policy(apply_object=host.provider)

        if cluster:
            rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    # Update hc map in Status Server
    status_scenarios.reset_hc_map()
    # Send events
    status_scenarios.notify_about_redistributed_concerns_from_maps(added=concern_map, removed={})

    if concern_id:
        status_scenarios.notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return host.pk


def _create_provider(prototype: Prototype, name: str, description: str, config_service: core.config.ConfigService):
    provider = Provider.objects.create(prototype=prototype, name=name, description=description)
    descriptor = CoreObjectDescriptor(id=provider.pk, type=ADCMCoreType.PROVIDER)
    config_service.create_initial_configuration_if_required(owner=descriptor)
    return provider
