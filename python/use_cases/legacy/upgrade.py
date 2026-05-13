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

from functools import partial

from cm.converters import orm_object_to_core_descriptor
from cm.legacy.bundle_switch_revert import SwitchRevertCallbacks
from cm.models import Cluster, Component, Prototype, Service
from cm.transition.status import StatusScenarios
from rbac.scenarios import RBACScenarios
import core


def build_switch_revert_callbacks(
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
):
    # TODO
    #  Should be passed as dependency, but for now it's too complex.
    #  Fix within ADCM-7974.
    status_scenarios = StatusScenarios()

    return SwitchRevertCallbacks(
        add_component_to_service=partial(_add_component_to_service, config_service=config_service),
        add_service_to_cluster=partial(
            _add_service_to_cluster,
            config_service=config_service,
            rbac_scenarios=rbac_scenarios,
            status_scenarios=status_scenarios,
        ),
    )


def _add_service_to_cluster(
    cluster: Cluster,
    prototype: Prototype,
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> Service:
    from use_cases.transition.cluster.create import CreateServicesFromPrototypes

    service, *_ = CreateServicesFromPrototypes(
        config_service=config_service, rbac_scenarios=rbac_scenarios, status_scenarios=status_scenarios
    ).do(cluster=cluster, prototype_ids=(prototype.pk,))

    return service


def _add_component_to_service(
    service: Service, prototype: Prototype, config_service: core.config.ConfigService
) -> Component:
    component = Component.objects.create(
        cluster_id=service.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
        service=service,
        prototype=prototype,
    )
    descriptor = orm_object_to_core_descriptor(component)
    config_service.create_initial_configuration_if_required(owner=descriptor)

    return component
