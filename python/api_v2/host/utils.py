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

from cm.legacy.api import check_license
from cm.legacy.config import init_object_config
from cm.legacy.services.concern.cases import recalculate_own_concerns_on_add_hosts
from cm.legacy.services.concern.distribution import distribute_concern_from_provider_to_host
from cm.logger import logger
from cm.models import Cluster, Host, ObjectType, Prototype
from cm.transition.status import StatusScenarios
from core.types import ADCMCoreType, BundleID, ProviderID
from rbac.scenarios import RBACScenarios


def create_host(
    bundle_id: BundleID,
    provider_id: ProviderID,
    fqdn: str,
    cluster: Cluster | None,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios | None = None,
) -> Host:
    status_scenarios = status_scenarios or StatusScenarios()
    host_prototype = Prototype.objects.get(type=ObjectType.HOST, bundle_id=bundle_id)
    check_license(prototype=host_prototype)

    host = Host.objects.create(prototype=host_prototype, provider_id=provider_id, fqdn=fqdn, cluster=cluster)

    obj_conf = init_object_config(proto=host.prototype, obj=host)
    host.config = obj_conf
    host.save(update_fields=["config"])

    concern_map = {ADCMCoreType.HOST: {host.id: set()}}
    host_concern_map = recalculate_own_concerns_on_add_hosts(host=host)

    if host_concern_map:
        concern_id = next(iter(host_concern_map[ADCMCoreType.HOST][host.id]))
        host.concerns.add(concern_id)
        concern_map[ADCMCoreType.HOST][host.id].add(concern_id)

    attached_concern_map = distribute_concern_from_provider_to_host(host_id=host.id)

    if attached_concern_map:
        concern_map[ADCMCoreType.HOST][host.id] |= attached_concern_map[ADCMCoreType.HOST][host.id]

    rbac_scenarios.re_apply_object_policy(apply_object=host.provider)

    if cluster := host.cluster:
        rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    status_scenarios.reset_hc_map()
    status_scenarios.notify_about_redistributed_concerns_from_maps(added=concern_map, removed={})

    if cluster:
        logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)
    else:
        logger.info("host #%s %s is added", host.pk, host.fqdn)

    return host
