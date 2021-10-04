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

"""Possible Methods specification"""
from collections.abc import Callable
from enum import Enum
from http import HTTPStatus

import attr
import requests

_OBJECTS_URL_TEMPLATE = "/{name}/"
_OBJECT_URL_TEMPLATE = "/{name}/{id}/"


@attr.dataclass
class Method:  # pylint: disable=too-few-public-methods
    """Describe possible methods and how they are used in ADCM api"""

    function: Callable
    url_template: str
    default_success_code: int = HTTPStatus.OK


class Methods(Enum):
    """All possible methods"""

    def __init__(self, method: Method):
        self.method = method

    @property
    def function(self):
        """Getter for Method.function attribute"""
        return self.method.function

    @property
    def url_template(self):
        """Getter for Method.url_template attribute"""
        return self.method.url_template

    @property
    def default_success_code(self):
        """Getter for Method.default_success_code attribute"""
        return self.method.default_success_code

    GET = Method(function=requests.get, url_template=_OBJECT_URL_TEMPLATE)
    LIST = Method(function=requests.get, url_template=_OBJECTS_URL_TEMPLATE)
    POST = Method(
        function=requests.post,
        url_template=_OBJECTS_URL_TEMPLATE,
        default_success_code=HTTPStatus.CREATED,
    )
    PUT = Method(function=requests.put, url_template=_OBJECT_URL_TEMPLATE)
    PATCH = Method(function=requests.patch, url_template=_OBJECT_URL_TEMPLATE)
    DELETE = Method(
        function=requests.delete,
        url_template=_OBJECT_URL_TEMPLATE,
        default_success_code=HTTPStatus.NO_CONTENT,
    )
