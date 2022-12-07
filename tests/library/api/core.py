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

from typing import Literal

from requests import Response, post


class RequestResult:
    def __init__(self, response: Response):
        self.response = response
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = self.response.json()
        return self._data

    def __getitem__(self, item):
        return self.data[item]

    def check_code(self, expected: int) -> "RequestResult":
        assert (
            self.response.status_code == expected
        ), f"Incorrect request status code.\nActual: {self.response.status_code}\nExpected: {expected}"
        return self


class Requester:
    def __init__(self, url: str):
        self.base_url = url
        self.auth_header: dict[Literal["Authorization"], str] = {}

    @staticmethod
    def _build_header(token: str) -> dict[str, str]:
        return {"Authorization": f"Token {token}"}

    def get_auth_header(self, credentials: dict[str, str]) -> dict[str, str]:
        token = self.post("token", json=credentials, authorized=False)["token"]
        return self._build_header(token)

    def post(self, *path: str, authorized: bool = True, **request_kwargs) -> RequestResult:
        if authorized:
            if not self.auth_header:
                raise RuntimeError("Authorization header is not initialized")
            if "headers" not in request_kwargs:
                request_kwargs["headers"] = self.auth_header
            elif "Authorization" not in request_kwargs["headers"]:
                request_kwargs["headers"]["Authorization"] = self.auth_header["Authorization"]

        return RequestResult(post(f"{'/'.join((self.base_url, *path))}/", **request_kwargs))


class Node:
    def __init__(self, requester: Requester):
        self._requester = requester
