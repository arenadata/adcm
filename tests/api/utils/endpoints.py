"""ADCM Endpoints classes and methods"""

# pylint: disable=too-few-public-methods,invalid-name
from enum import Enum
from typing import List, Type, Optional

import attr

from .data_classes import (
    BaseClass,
    ConfigGroupFields,
    HostGroupFields,
    HostFields,
    ClusterFields,
    ServiceFields,
    ComponentFields,
    ProviderFields, ObjectConfigFields, ConfigLogFields
)
from .methods import Methods
from .types import get_fields


@attr.dataclass
class Endpoint:
    """Endpoint class

    :attribute path: endpoint name
    :attribute methods: list of allowed methods for endpoint
    :attribute data_class: endpoint fields specification
    :attribute spec_link: link to ADCM specification for endpoint
    :attribute technical: pass True if need to ignore during collect tests
    """

    path: str
    methods: List[Methods]
    data_class: Type[BaseClass]
    spec_link: str
    technical: bool = False


class Endpoints(Enum):
    """All current endpoints"""

    def __init__(self, endpoint: Endpoint):
        self.endpoint = endpoint

    @property
    def path(self):
        """Getter for Endpoint.path attribute"""
        return self.endpoint.path

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

    def get_child_endpoint_by_fk_name(self, field_name: str) -> Optional["Endpoints"]:
        """Get endpoint instance by data class"""
        for field in get_fields(self.value.data_class):  # pylint: disable=no-member
            if field.name == field_name:
                try:
                    return self.get_by_data_class(field.f_type.fk_link)
                except AttributeError:
                    raise ValueError(
                        f"Field {field_name} must be a Foreign Key field type"
                    ) from AttributeError
        return None

    Cluster = Endpoint(
        path="cluster",
        methods=[Methods.LIST, Methods.GET],
        data_class=ClusterFields,
        spec_link="",
        technical=True
    )

    Service = Endpoint(
        path="service",
        methods=[Methods.LIST, Methods.GET],
        data_class=ServiceFields,
        spec_link="",
        technical=True
    )

    Component = Endpoint(
        path="component",
        methods=[Methods.LIST, Methods.GET],
        data_class=ComponentFields,
        spec_link="",
        technical=True
    )

    Provider = Endpoint(
        path="provider",
        methods=[Methods.LIST, Methods.GET],
        data_class=ProviderFields,
        spec_link="",
        technical=True
    )

    Host = Endpoint(
        path="host",
        methods=[Methods.LIST, Methods.GET],
        data_class=HostFields,
        spec_link="",
        technical=True
    )

    ObjectConfig = Endpoint(
        path="object-config",
        methods=[
            Methods.GET, Methods.LIST
        ],
        data_class=ObjectConfigFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#object-config",
    )

    ConfigLog = Endpoint(
        path="config-log",
        methods=[
            Methods.GET, Methods.LIST, Methods.POST
        ],
        data_class=ConfigLogFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#object-config",
    )

    ConfigGroup = Endpoint(
        path="config-group",
        methods=[
            Methods.GET, Methods.LIST, Methods.POST, Methods.PUT, Methods.PATCH, Methods.DELETE
        ],
        data_class=ConfigGroupFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#config-group",
    )

    HostGroup = Endpoint(
        path="host-group",
        methods=[
            Methods.GET, Methods.LIST, Methods.POST, Methods.PUT, Methods.PATCH, Methods.DELETE
        ],
        data_class=HostGroupFields,
        spec_link="https://spec.adsw.io/adcm_core/objects.html#host-group",
    )
