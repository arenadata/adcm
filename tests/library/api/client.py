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
from contextlib import contextmanager

from tests.library.api.core import Requester
from tests.library.api.nodes import ComponentNode, HostNode, ServiceNode


class APIClient(Requester):
    def __init__(self, url: str, credentials: dict[str, str]):
        super().__init__(f"{url}/api/v1")
        self.auth_header = self.get_auth_header(credentials)
        self.host = HostNode(self)
        self.service = ServiceNode(self)
        self.component = ComponentNode(self)

    @contextmanager
    def logged_as_another_user(self, *, token: str):
        original_header = {**self.auth_header}
        self.auth_header = self._build_header(token)
        yield
        self.auth_header = original_header
