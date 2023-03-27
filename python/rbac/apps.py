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

"""RBAC Django application"""

from django.apps import AppConfig


class RBACConfig(AppConfig):
    """RBAC app config"""

    name = "rbac"
    verbose_name = "Arenadata Web Platform role-based access control"

    def ready(self):
        # pylint: disable-next=import-outside-toplevel,unused-import
        from cm.signals import mark_deleted_audit_object_handler  # noqa: F401
