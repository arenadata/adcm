"""ADSS Endpoints classes and methods"""

# pylint: disable=too-few-public-methods,invalid-name
from enum import Enum
from typing import List, Type, Optional

import attr

from .data_classes import (
    ClusterTypeFields,
    ClusterFields,
    ClusterCapacityFields,
    ResourceTypeFields,
    FileSystemFields,
    FileSystemCapacityFields,
    FileSystemTypeFields,
    HandlerFields,
    ClusterConsumptionFields,
    FileSystemConsumptionFields,
    CronLineFields,
    JobQueueFields,
    JobHistoryFields,
    MountPointFields,
    BaseClass,
)
from .methods import Methods
from .types import get_fields


@attr.dataclass
class Endpoint:
    """Endpoint class

    :attribute path: endpoint name
    :attribute methods: list of allowed methods for endpoint
    :attribute data_class: endpoint fields specification
    :attribute spec_link: link to ADSS specification for endpoint
    :attribute ignored: reason why this endpoint should not be tested
    """

    path: str
    methods: List[Methods]
    data_class: Type[BaseClass]
    spec_link: str
    ignored: str = None


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
    def ignored(self):
        """Getter for Endpoint.ignored attribute"""
        return self.endpoint.ignored

    @classmethod
    def get_by_data_class(cls, data_class: Type[BaseClass]) -> Optional["Endpoints"]:
        """Get endpoint instance by data class"""
        for endpoint in cls:
            if endpoint.data_class == data_class:
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

    ResourceType = Endpoint(
        path="resource-type",
        methods=[Methods.GET, Methods.LIST],
        data_class=ResourceTypeFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#resource-type",
    )

    ClusterType = Endpoint(
        path="cluster-type",
        methods=[Methods.GET, Methods.LIST],
        data_class=ClusterTypeFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#cluster-type",
    )

    Cluster = Endpoint(
        path="cluster",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=ClusterFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#cluster",
    )

    ClusterCapacity = Endpoint(
        path="cluster-capacity",
        methods=[Methods.GET, Methods.LIST, Methods.PUT, Methods.PATCH],
        data_class=ClusterCapacityFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#cluster-capacity",
    )

    FileSystemType = Endpoint(
        path="filesystem-type",
        methods=[Methods.GET, Methods.LIST],
        data_class=FileSystemTypeFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#filesystem-type",
    )

    FileSystem = Endpoint(
        path="filesystem",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=FileSystemFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#filesystem",
    )

    FileSystemCapacity = Endpoint(
        path="filesystem-capacity",
        methods=[Methods.GET, Methods.LIST, Methods.PUT, Methods.PATCH],
        data_class=FileSystemCapacityFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#filesystem-capacity",
    )

    MountPoint = Endpoint(
        path='mount-point',
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=MountPointFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#mount-point",
    )

    Handler = Endpoint(
        path="handler",
        methods=[Methods.GET, Methods.LIST],
        data_class=HandlerFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#handler",
    )

    ClusterConsumption = Endpoint(
        path="cluster-consumption",
        methods=[Methods.GET, Methods.LIST],
        data_class=ClusterConsumptionFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#cluster-consumption",
    )

    FileSystemConsumption = Endpoint(
        path="filesystem-consumption",
        methods=[Methods.GET, Methods.LIST],
        data_class=FileSystemConsumptionFields,
        spec_link="https://spec.adsw.io/adss_core/objects.html#filesystem-consumption",
    )

    CronLine = Endpoint(
        path="cron-line",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
            Methods.DELETE,
        ],
        data_class=CronLineFields,
        spec_link="https://spec.adsw.io/adss_core/scheduler.html#cron-line",
    )

    JobQueue = Endpoint(
        path="job-queue",
        methods=[
            Methods.GET,
            Methods.LIST,
            Methods.POST,
            Methods.PUT,
            Methods.PATCH,
        ],
        data_class=JobQueueFields,
        spec_link="https://spec.adsw.io/adss_core/scheduler.html#job-queue",
    )

    JobHistory = Endpoint(
        path="job-history",
        methods=[Methods.GET, Methods.LIST],
        data_class=JobHistoryFields,
        spec_link="https://spec.adsw.io/adss_core/scheduler.html#job-history",
    )
