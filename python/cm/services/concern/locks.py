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

from core.types import CoreObjectDescriptor

from cm.converters import core_type_to_model
from cm.models import Cluster, Component, ConcernItem, ConcernType, Host, Provider, Service


def get_lock_on_object(object_: Cluster | Service | Component | Provider | Host) -> ConcernItem | None:
    return object_.concerns.filter(type=ConcernType.LOCK).first()


def retrieve_lock_on_object(object_: CoreObjectDescriptor) -> ConcernItem | None:
    object_model = core_type_to_model(core_type=object_.type)
    id_field = f"{object_model.__name__.lower()}_id"

    related_locks_qs = object_model.concerns.through.objects.filter(
        concernitem__type=ConcernType.LOCK, **{id_field: object_.id}
    ).values_list("concernitem_id", flat=True)

    return ConcernItem.objects.filter(id__in=related_locks_qs).first()
