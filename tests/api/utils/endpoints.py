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

"""ADCM Endpoints classes and methods"""

from enum import Enum
from typing import Callable, List, Optional, Type

import attr
from tests.api.utils.data_classes import (
    BaseClass,
    ClusterFields,
    ComponentFields,
    ConfigLogFields,
    GroupConfigFields,
    GroupConfigHostCandidatesFields,
    GroupConfigHostsFields,
    HostFields,
    ObjectConfigFields,
    ProviderFields,
    RbacBuiltInPolicyFields,
    RbacBuiltInRoleFields,
    RbacBusinessRoleFields,
    RbacGroupFields,
    RbacNotBuiltInPolicyFields,
    RbacSimpleRoleFields,
    RbacUserFields,
    ServiceFields,
)
from tests.api.utils.filters import (
    is_built_in,
    is_business_role,
    is_not_built_in,
    is_not_business_role,
    is_not_hidden_role,
    is_role_type,
)
from tests.api.utils.methods import Methods
from tests.api.utils.types import get_fields

ALL = [
    Methods.GET,
    Methods.LIST,
    Methods.POST,
    Methods.PUT,
    Methods.PATCH,
    Methods.DELETE,
]


@attr.dataclass
class Endpoint:
    """Endpoint class

    :attribute path: endpoint name
    :attribute methods: list of allowed methods for endpoint
    :attribute data_class: endpoint fields specification
    :attribute spec_link: link to ADCM specification for endpoint
    :attribute technical: pass True if need to ignore during collect tests
    :attribute filter_predicate: function that can be called to filter elements.
                                 If there's 0 existing objects, framework will try to create one and most likely fail
                                 with ValidationError in case object can't be created via API.
    """

    path: str
    methods: List[Methods]
    data_class: Type[BaseClass]
    spec_link: str
    technical: bool = False
    filter_predicate: Optional[Callable[[dict], bool]] = None
    _base_path = None

    def set_path(self, value):
        """Dynamically change a path, for example, insert parent object id into path"""
        if not self._base_path:
            self._base_path = self.path
        self.path = value

    def clear_path(self):
        """Revert path to initial generic value"""
        if self._base_path:
            self.path = self._base_path

    def get_data_class_pretty_name(self) -> str:
        """Get "pretty" data class name (without "Fields" suffix)"""
        return self.data_class.__name__.replace("Fields", "")


class Endpoints(Enum):
    """All current endpoints"""

    def __init__(self, endpoint: Endpoint):
        self.endpoint = endpoint

    @property
    def path(self):
        """Getter for Endpoint.path attribute"""
        return self.endpoint.path

    @path.setter
    def path(self, value):
        self.endpoint.set_path(value)

    @property
    def methods(self):
        """Getter for Endpoint.methods attribute"""
        return self.endpoint.methods

    @property
    def data_class(self):
        """Getter for Endpoint.data_class attribute"""
        return self.endpoint.data_class

    @property
    def spec_link(self):
        """Getter for Endpoint.spec_link attribute"""
        return self.endpoint.spec_link

    @property
    def technical(self):
        """Getter for Endpoint.technical attribute"""
        return self.endpoint.technical

    @property
    def endpoint_id(self) -> str:
        """Get endpoint identifier based on path and (if required) Data Class name"""
        path_id = self.endpoint.path.replace('/', '_')
        if sum(1 for e in Endpoints if e.path == self.endpoint.path) > 1:
            return f"{path_id}_{self.endpoint.get_data_class_pretty_name()}"
        return path_id

    @classmethod
    def get_by_data_class(cls, data_class: Type[BaseClass]) -> Optional["Endpoints"]:
        """Get endpoint instance by data class"""
        for endpoint in cls:
            if endpoint.data_class == data_class:
                return endpoint
        return None

    @classmethod
    def get_by_path(cls, path: str) -> Optional["Endpoints"]:
        """Get endpoint instance by API path"""
        for endpoint in cls:
            if endpoint.path == path:
                return endpoint
        return None

    @classmethod
    def clear_endpoints_paths(cls):
        """Revert endpoints path on initial value"""
        for endpoint in cls:
            endpoint.value.clear_path()

    def get_child_endpoint_by_fk_name(self, field_name: str) -> Optional["Endpoints"]:
        """Get child endpoint instance by data class"""
        for field in get_fields(self.value.data_class):
            if field.name == field_name:
                try:
                    return self.get_by_data_class(field.f_type.fk_link)
                except AttributeError:
                    raise ValueError(f"Field {field_name} must be a Foreign Key field type") from AttributeError
        return None

    Cluster = Endpoint(
        path="cluster",
        methods=[Methods.LIST, Methods.GET],
        data_class=ClusterFields,
        spec_link="",
        technical=True,
    )

    Service = Endpoint(
        path="service",
        methods=[Methods.LIST, Methods.GET],
        data_class=ServiceFields,
        spec_link="",
        technical=True,
    )

    Component = Endpoint(
        path="component",
        methods=[Methods.LIST, Methods.GET],
        data_class=ComponentFields,
        spec_link="",
        technical=True,
    )

    Provider = Endpoint(
        path="provider",
        methods=[Methods.LIST, Methods.GET],
        data_class=ProviderFields,
        spec_link="",
        technical=True,
    )

    Host = Endpoint(
        path="host",
        methods=[Methods.LIST, Methods.GET],
        data_class=HostFields,
        spec_link="",
        technical=True,
    )

    ObjectConfig = Endpoint(
        path="config",
        methods=[Methods.GET, Methods.LIST],
        data_class=ObjectConfigFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#object-config",
    )

    ConfigLog = Endpoint(
        path="config-log",
        methods=[Methods.GET, Methods.LIST, Methods.POST],
        data_class=ConfigLogFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#object-config",
    )

    GroupConfig = Endpoint(
        path="group-config",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=GroupConfigFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#group-config",
    )

    GroupConfigHosts = Endpoint(
        path=f"{GroupConfig.path}/{{id}}/host",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.DELETE,
        ],
        data_class=GroupConfigHostsFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#group-config-hosts",
    )

    GroupConfigHostCandidates = Endpoint(
        path=f"{GroupConfig.path}/{{id}}/host-candidate",
        methods=[
            Methods.GET,
            Methods.LIST,
        ],
        data_class=GroupConfigHostCandidatesFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html",
    )

    RbacUser = Endpoint(
        path="rbac/user",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        # deletion doesn't work here
        filter_predicate=lambda i: not i['built_in'],
        data_class=RbacUserFields,
        spec_link="",
    )

    RbacGroup = Endpoint(
        path="rbac/group",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=RbacGroupFields,
        spec_link="",
    )

    # Test logic for "not built_in" that can be created and have a child
    RbacSimpleRole = Endpoint(
        path="rbac/role",
        methods=ALL,
        data_class=RbacSimpleRoleFields,
        spec_link="",
        filter_predicate=lambda i: is_not_business_role(i) and is_not_hidden_role(i) and is_not_built_in(i),
    )

    # Test logic for "built_in"
    RbacBuiltInRole = Endpoint(
        path="rbac/role",
        methods=[Methods.GET, Methods.LIST, Methods.POST],
        data_class=RbacBuiltInRoleFields,
        spec_link="",
        filter_predicate=is_built_in,
        technical=True,
    )

    RbacBusinessRole = Endpoint(
        path="rbac/role",
        methods=[Methods.GET, Methods.LIST],
        data_class=RbacBusinessRoleFields,
        spec_link="",
        filter_predicate=is_business_role,
        technical=True,
    )

    # Workaround to get roles with 'role' type
    RbacAnyRole = Endpoint(
        path="rbac/role",
        methods=ALL,
        data_class=RbacSimpleRoleFields,
        spec_link="",
        technical=True,
        filter_predicate=is_role_type,
    )

    RbacNotBuiltInPolicy = Endpoint(
        path="rbac/policy",
        methods=ALL,
        data_class=RbacNotBuiltInPolicyFields,
        spec_link="",
        filter_predicate=is_not_built_in,
    )

    RbacBuiltInPolicy = Endpoint(
        path="rbac/policy",
        methods=[Methods.GET, Methods.LIST, Methods.POST],
        data_class=RbacBuiltInPolicyFields,
        spec_link="",
        technical=True,
        filter_predicate=is_built_in,
    )
