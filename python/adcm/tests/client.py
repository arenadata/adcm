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

from abc import ABC, abstractmethod
from itertools import chain
from typing import Protocol

from cm.models import (
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    HostProvider,
    JobLog,
    LogStorage,
    Prototype,
    Service,
    TaskLog,
)
from django.test.client import AsyncClient
from rbac.models import Group, Policy, Role, User
from rest_framework.response import Response
from rest_framework.test import APIClient

_RootPathObject = Bundle | Cluster | HostProvider | Host | TaskLog | JobLog | Prototype
PathObject = _RootPathObject | Service | Component | LogStorage | ConfigHostGroup


class WithID(Protocol):
    id: int


API_NODES_SLOTS = ("_client", "_path", "_resolved_path", "_node_class")


class APINode:
    __slots__ = API_NODES_SLOTS

    def __init__(self, *path: str, client: APIClient | AsyncClient, node_class: type["APINode"] | type["AsyncAPINode"]):
        self._client = client
        self._path = tuple(path)
        self._resolved_path = None
        self._node_class = node_class

    def __truediv__(self, other: str | int | WithID):
        if isinstance(other, (str, int)):
            return self._node_class(*self._path, str(other), client=self._client, node_class=self._node_class)

        return self._node_class(*self._path, str(other.id), client=self._client, node_class=self._node_class)

    @property
    def path(self) -> str:
        if self._resolved_path:
            return self._resolved_path

        cleaned_path_parts = filter(bool, chain.from_iterable(sub_path.split("/") for sub_path in self._path))
        self._resolved_path = f"/{'/'.join(cleaned_path_parts)}/"

        return self._resolved_path

    def get(self, *, query: dict | None = None, headers: dict | None = None) -> Response:
        return self._client.get(path=self.path, data=query, **(headers or {}))

    def post(
        self, *, data: dict | list[dict] | None = None, headers: dict | None = None, format_: str | None = None
    ) -> Response:
        return self._client.post(path=self.path, data=data, format=format_, **(headers or {}))

    def patch(self, *, data: dict, headers: dict | None = None) -> Response:
        return self._client.patch(path=self.path, data=data, **(headers or {}))

    def delete(self, headers: dict | None = None) -> Response:
        return self._client.delete(path=self.path, **(headers or {}))


class AsyncAPINode(APINode):
    __slots__ = API_NODES_SLOTS

    def post(self, *, data: dict | list[dict] | None = None, format_: str | None = None) -> Response:
        return self._client.post(path=self.path, data=data, content_type=format_)


class RootNode(APINode, ABC):
    @abstractmethod
    def __getitem__(self, item) -> APINode:
        ...


class V2RootNode(RootNode):
    _CLASS_ROOT_EP_MAP = {
        Bundle: "bundles",
        Cluster: "clusters",
        HostProvider: "hostproviders",
        Host: "hosts",
        TaskLog: "tasks",
        JobLog: "jobs",
        Prototype: "prototypes",
        Policy: "rbac/policies",
        User: "rbac/users",
        Role: "rbac/roles",
        Group: "rbac/groups",
        "profile": "profile",
        "adcm": "adcm",
        "schema": "schema",
        "token": "token",
        "audit-login": "audit/logins",
    }

    def __getitem__(self, item: PathObject | tuple[PathObject, str | int | WithID, ...]) -> APINode:
        if isinstance(item, tuple):
            path_object, *tail_ = item
            tail = tuple(str(entry) if isinstance(entry, (str, int)) else str(entry.id) for entry in tail_)
        else:
            path_object, tail = item, ()

        if isinstance(path_object, str):
            root_endpoint = self._CLASS_ROOT_EP_MAP.get(path_object)
            object_id_path = ()
        else:
            root_endpoint = self._CLASS_ROOT_EP_MAP.get(path_object.__class__)
            object_id_path = (str(path_object.id),)

        if root_endpoint:
            return self._node_class(
                *self._path, root_endpoint, *object_id_path, *tail, client=self._client, node_class=self._node_class
            )

        if isinstance(path_object, Service):
            return self._node_class(
                *self._path,
                "clusters",
                str(path_object.cluster_id),
                "services",
                str(path_object.id),
                *tail,
                client=self._client,
                node_class=self._node_class,
            )

        if isinstance(path_object, Component):
            return self._node_class(
                *self._path,
                "clusters",
                str(path_object.cluster_id),
                "services",
                str(path_object.service_id),
                "components",
                str(path_object.id),
                *tail,
                client=self._client,
                node_class=self._node_class,
            )

        if isinstance(path_object, ConfigHostGroup):
            # generally it's move clean and obvious when multiple `/` is used, but in here it looks like an overkill
            return self[path_object.object] / "/".join(("config-groups", str(path_object.id), *tail))

        if isinstance(path_object, ActionHostGroup):
            return self[path_object.object] / "/".join(("action-host-groups", str(path_object.id), *tail))

        if isinstance(path_object, LogStorage):
            return self._node_class(
                *self._path,
                "jobs",
                str(path_object.job_id),
                "logs",
                str(path_object.id),
                *tail,
                client=self._client,
                node_class=self._node_class,
            )

        message = f"Node auto-detection isn't defined for {path_object.__class__}"
        raise NotImplementedError(message)


class ADCMTestClient(APIClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.versions = APINode("versions", client=self, node_class=APINode)
        self.v2 = V2RootNode("api", "v2", client=self, node_class=APINode)


class ADCMAsyncTestClient(AsyncClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.versions = APINode("versions", client=self, node_class=APINode)
        self.v2 = V2RootNode("api", "v2", client=self, node_class=AsyncAPINode)
