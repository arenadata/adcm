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

from audit.alt.api import audit_update, audit_view
from audit.alt.core import RetrieveAuditObjectFunc


def audit_config_viewset(type_in_name: str, retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(create=audit_update(name=f"{type_in_name} configuration updated", object_=retrieve_owner))
