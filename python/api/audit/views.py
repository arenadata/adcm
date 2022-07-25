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


from api.base_view import PaginatedView

from audit.models import AuditLog
from . import serializers


class AuditLogListView(PaginatedView):
    """
    get:
    List of all auditlog entities
    """

    queryset = AuditLog.objects.select_related('audit_object_id', 'user').all()
    serializer_class = serializers.AuditLogSerializer
