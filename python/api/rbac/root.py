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

"""Arenadata RBAC root view"""

from rest_framework import permissions, routers


class RBACRoot(routers.APIRootView):
    """Arenadata RBAC Root"""

    permission_classes = (permissions.AllowAny,)
    api_root_dict = {
        "me": "me",
        "user": "user-list",
        "group": "group-list",
        "role": "role-list",
        "policy": "policy-list",
        "logout": "logout",
        "token": "token",
    }
