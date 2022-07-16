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

from cm.models.action import Action, SubAction
from cm.models.base import (
    ADCM,
    ADCMEntity,
    ADCMModel,
    Bundle,
    ConcernItem,
    DummyData,
    ObjectConfig,
    ProductCategory,
    Prototype,
    Upgrade,
    UserProfile,
)
from cm.models.cluster import (
    Cluster,
    ClusterBind,
    ClusterObject,
    get_object_cluster,
    ServiceComponent,
)
from cm.models.get_model_by_type import get_model_by_type
from cm.models.host import Host, HostComponent, HostProvider
from cm.models.log import (
    CheckLog,
    ConfigLog,
    GroupCheckLog,
    GroupConfig,
    JobLog,
    LogStorage,
    MessageTemplate,
    TaskLog,
    validate_line_break_character,
)
from cm.models.prototype import PrototypeConfig, PrototypeExport, PrototypeImport
from cm.models.stage import (
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
)
from cm.models.types import (
    ActionType,
    ConcernCause,
    ConcernType,
    MaintenanceModeType,
    PrototypeEnum,
)
from cm.models.utils import (
    get_any,
    get_default_before_upgrade,
    get_default_constraint,
    get_default_from_edition,
)
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver


@receiver(post_delete, sender=ServiceComponent)
def auto_delete_config_with_servicecomponent(sender, instance, **kwargs):
    if instance.config is not None:
        instance.config.delete()


@receiver(m2m_changed, sender=GroupConfig.hosts.through)
def verify_host_candidate_for_group_config(sender, **kwargs):
    """Checking host candidate for group config before add to group"""
    group_config = kwargs.get('instance')
    action = kwargs.get('action')
    host_ids = kwargs.get('pk_set')

    if action == 'pre_add':
        for host_id in host_ids:
            host = Host.objects.get(id=host_id)
            group_config.check_host_candidate(host)
