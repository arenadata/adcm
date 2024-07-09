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
from django.contrib.contenttypes.models import ContentType

from cm.converters import core_type_to_model
from cm.models import ConcernCause, ConcernItem, ConcernType


def delete_issue(owner: CoreObjectDescriptor, cause: ConcernCause) -> None:
    owner_type = ContentType.objects.get_for_model(core_type_to_model(core_type=owner.type))
    ConcernItem.objects.filter(owner_id=owner.id, owner_type=owner_type, cause=cause, type=ConcernType.ISSUE).delete()
