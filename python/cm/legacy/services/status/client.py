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

from core.status import FullStatusMap
from pydantic import ValidationError
from requests import JSONDecodeError

from cm.legacy.status_api import api_request

# pylint: enable=invalid-name


def retrieve_status_map() -> FullStatusMap:
    response = api_request(method="get", url="all/")
    if not response:
        return FullStatusMap()

    try:
        body = response.json()
    except JSONDecodeError:
        return FullStatusMap()

    if not isinstance(body, dict):
        return FullStatusMap()

    try:
        return FullStatusMap(**body)
    except ValidationError:
        return FullStatusMap()
