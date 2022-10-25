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

"""Stack endpoint root view"""

from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView


class StackRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "load": "load-bundle",
        "upload": "upload-bundle",
        "bundle": "bundle-list",
        "prototype": "prototype-list",
        "service": "service-prototype-list",
        "host": "host-prototype-list",
        "provider": "provider-prototype-list",
        "cluster": "cluster-prototype-list",
    }
