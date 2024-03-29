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

import re

from cm.errors import raise_adcm_ex
from django.db.models.signals import pre_save
from django.dispatch import receiver

from rbac.models import Group, OriginType
from rbac.utils import get_group_name_display_name


@receiver(signal=pre_save, sender=Group)
def handle_name_type_display_name(sender, instance, **kwargs):  # noqa: ARG001
    if kwargs["raw"]:
        return

    base_group_name_pattern = re.compile(rf'(?P<base_name>.*?)(?: \[(?:{"|".join(OriginType.values)})\]|$)')
    match = base_group_name_pattern.match(instance.name)
    if match and match.group("base_name"):
        name, display_name = get_group_name_display_name(name=match.group("base_name"), type_=instance.type)
        instance.name = name
        instance.display_name = display_name
    else:
        raise_adcm_ex(code="GROUP_CONFLICT", msg=f"Check regex. Data: `{instance.name}`")
