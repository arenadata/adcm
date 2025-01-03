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

from django.apps import AppConfig
from django.db.models import Field

from cm.lookups import CaseInsensitiveNotEqualLookup, LowerCaseTransform, NotEqualLookup


class CmConfig(AppConfig):
    name = "cm"
    verbose_name = "cm"

    def ready(self):
        from cm.signals import (  # noqa: F401, PLC0415
            rename_audit_object,
            rename_audit_object_host,
        )

        Field.register_lookup(NotEqualLookup)
        Field.register_lookup(CaseInsensitiveNotEqualLookup)
        Field.register_lookup(LowerCaseTransform)
