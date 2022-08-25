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

from django.db.models.signals import post_delete
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from audit.models import MODEL_TO_AUDIT_OBJECT_TYPE_MAP
from audit.utils import mark_deleted_audit_object
from rbac.models import Group, Policy, Role, User


@receiver(post_delete, sender=User)
@receiver(post_delete, sender=Group)
@receiver(post_delete, sender=Policy)
@receiver(post_delete, sender=Role)
@receiver(post_delete, sender=Token)
def mark_deleted_audit_object_handler(sender, instance, **kwargs):
    mark_deleted_audit_object(instance, object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender])
