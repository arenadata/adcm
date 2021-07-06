"""Endpoint data classes definition"""
# pylint: disable=too-few-public-methods
from datetime import datetime

from abc import ABC
from typing import List

from .types import (
    Field,
    PositiveInt,
    String,
    Text,
    Json,
    DateTime,
    Enum,
    CronLine,
    ForeignKey,
    ForeignKeyM2M,
    BackReferenceFK,
    Relation,
)


class BaseClass(ABC):
    """Base data class"""

    # List of BaseClass that are NOT included in POST method for current Class
    # but should exist before data preparation
    # and creation of current object
    # Ex. ClusterCapacity can only be created implicitly during Cluster creation
    predefined_dependencies: List["BaseClass"] = []

    # List of BaseClass that are NOT included in POST method for current Class
    # and should be generated implicitly after data preparation
    # and creation of current object
    # Ex. MountPoint is not included in CronLine class but should exist before CronLine creation
    implicitly_depends_on: List["BaseClass"] = []


class ResourceTypeFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#resource-type
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))
    display_name = Field(name="display_name", f_type=String(), default_value=name)
    short_description = Field(name="short_description", f_type=Text())
    description = Field(name="description", f_type=Text())


class ClusterTypeFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#cluster-type
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))
    display_name = Field(name="display_name", f_type=String(), default_value=name)
    short_description = Field(name="short_description", f_type=Text())
    description = Field(name="description", f_type=Text())
    connection_schema = Field(name="connection_schema", f_type=Json())


class ClusterFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#cluster
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(
        name="name", f_type=String(max_length=255), changeable=True, postable=True, required=True
    )
    display_name = Field(
        name="display_name", f_type=String(), changeable=True, postable=True, default_value=name
    )
    connection = Field(
        name="connection",
        f_type=Json(relates_on=Relation(ClusterTypeFields, ClusterTypeFields.connection_schema)),
        changeable=True,
        postable=True,
        required=True,
    )
    cluster_type = Field(
        name="cluster_type",
        f_type=ForeignKey(fk_link=ClusterTypeFields),
        postable=True,
        required=True,
    )


class ClusterCapacityFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#cluster-capacity
    """

    predefined_dependencies = [ClusterFields]

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    label = Field(name="label", f_type=Enum(enum_values=["on-demand", "cron"]), required=True)
    value = Field(name="value", f_type=PositiveInt(), default_value=1, changeable=True)
    resource_type = Field(
        name="resource_type", f_type=ForeignKey(fk_link=ResourceTypeFields), required=True
    )
    cluster = Field(name="cluster", f_type=ForeignKey(fk_link=ClusterFields), required=True)


# Back-reference from ClusterCapacity
ClusterFields.cluster_capacity = Field(
    name="cluster_capacity",
    f_type=BackReferenceFK(fk_link=ClusterCapacityFields),
    default_value="auto",
)


class FileSystemTypeFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#file-system-type
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))
    display_name = Field(name="display_name", f_type=String(), default_value=name)
    short_description = Field(name="short_description", f_type=Text())
    description = Field(name="description", f_type=Text())
    connection_schema = Field(name="connection_schema", f_type=Json())
    mount_point_schema = Field(name="mount_point_schema", f_type=Json())


class FileSystemFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#file-system
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(
        name="name", f_type=String(max_length=255), changeable=True, postable=True, required=True
    )
    display_name = Field(
        name="display_name", f_type=String(), changeable=True, postable=True, default_value=name
    )
    connection = Field(
        name="connection",
        f_type=Json(
            relates_on=Relation(FileSystemTypeFields, FileSystemTypeFields.connection_schema)
        ),
        changeable=True,
        postable=True,
        required=True,
    )
    filesystem_type = Field(
        name="filesystem_type",
        f_type=ForeignKey(fk_link=FileSystemTypeFields),
        postable=True,
        required=True,
    )


class FileSystemCapacityFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#file-system-capacity
    """

    predefined_dependencies = [FileSystemFields]

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    label = Field(name="label", f_type=Enum(enum_values=["on-demand", "cron"]), required=True)
    value = Field(name="value", f_type=PositiveInt(), default_value=1, changeable=True)
    resource_type = Field(
        name="resource_type", f_type=ForeignKey(fk_link=ResourceTypeFields), required=True
    )
    filesystem = Field(
        name="filesystem", f_type=ForeignKey(fk_link=FileSystemFields), required=True
    )


FileSystemFields.filesystem_capacity = Field(
    name="filesystem_capacity",
    f_type=BackReferenceFK(fk_link=FileSystemCapacityFields),
    default_value="auto",
)


class MountPointFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#mount-point
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    cluster = Field(
        name="cluster", f_type=ForeignKey(fk_link=ClusterFields), postable=True, required=True
    )
    filesystem = Field(
        name="filesystem", f_type=ForeignKey(fk_link=FileSystemFields), postable=True, required=True
    )
    connection = Field(
        name="connection",
        f_type=Json(
            relates_on=Relation(FileSystemTypeFields, FileSystemTypeFields.mount_point_schema)
        ),
        default_value={},
        postable=True,
        changeable=True,
        custom_required=True,
    )


FileSystemFields.mount_point = Field(
    name="mount_point", f_type=BackReferenceFK(fk_link=MountPointFields), default_value="auto"
)
ClusterFields.mount_point = Field(
    name="mount_point", f_type=BackReferenceFK(fk_link=MountPointFields), default_value="auto"
)


class HandlerFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#handler
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))
    display_name = Field(name="display_name", f_type=String(), default_value=name)
    short_description = Field(name="short_description", f_type=Text())
    description = Field(name="description", f_type=Text())
    type = Field(name="type", f_type=Enum(enum_values=["backup", "restore"]))
    handler_class = Field(name="handler_class", f_type=Json())
    cluster_type = Field(name="cluster_type", f_type=ForeignKeyM2M(fk_link=ClusterTypeFields))
    filesystem_type = Field(
        name="filesystem_type", f_type=ForeignKeyM2M(fk_link=FileSystemTypeFields)
    )
    config_schema = Field(name="config_schema", f_type=Json())


class ClusterConsumptionFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#cluster-consumption
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    value = Field(name="value", f_type=PositiveInt())
    resource_type = Field(name="resource_type", f_type=ForeignKey(fk_link=ResourceTypeFields))
    handler = Field(name="handler", f_type=ForeignKey(fk_link=HandlerFields))


HandlerFields.cluster_consumption = Field(
    name="cluster_consumption",
    f_type=BackReferenceFK(fk_link=ClusterConsumptionFields),
    default_value="auto",
)


class FileSystemConsumptionFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/objects.html#file-system-consumption
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    value = Field(name="value", f_type=PositiveInt())
    resource_type = Field(name="resource_type", f_type=ForeignKey(fk_link=ResourceTypeFields))
    handler = Field(name="handler", f_type=ForeignKey(fk_link=HandlerFields))


HandlerFields.filesystem_consumption = Field(
    name="filesystem_consumption",
    f_type=BackReferenceFK(fk_link=FileSystemConsumptionFields),
    default_value="auto",
)


class CronLineFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/adss-97/scheduler.html#cron-line
    """

    implicitly_depends_on = [MountPointFields]

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(
        name="name", f_type=String(max_length=255), changeable=True, postable=True, required=True
    )
    display_name = Field(
        name="display_name", f_type=String(), changeable=True, postable=True, default_value=name
    )
    handler = Field(
        name="handler", f_type=ForeignKey(fk_link=HandlerFields), postable=True, required=True
    )
    cluster = Field(
        name="cluster", f_type=ForeignKey(fk_link=ClusterFields), postable=True, required=True
    )
    filesystem = Field(
        name="filesystem", f_type=ForeignKey(fk_link=FileSystemFields), postable=True, required=True
    )
    config = Field(
        name="config",
        f_type=Json(relates_on=Relation(HandlerFields, HandlerFields.config_schema)),
        dynamic_nullable=True,
        changeable=True,
        postable=True,
        custom_required=True,
    )
    cron_line = Field(
        name="cron_line",
        f_type=CronLine(max_length=50),
        changeable=True,
        postable=True,
        required=True,
    )
    state = Field(
        name="state",
        f_type=Enum(enum_values=["active", "inactive"]),
        default_value="active",
        changeable=True,
        postable=True,
    )
    create_date = Field(name="create_date", f_type=DateTime(), default_value=datetime.now())
    last_run_date = Field(name="last_run_date", f_type=DateTime(), nullable=True)


class JobQueueFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/adss-97/scheduler.html#job-queue
    """

    # CronLine is a part of JobQueue object but not allowed to be POSTed
    # so we need to create it implicitly
    implicitly_depends_on = [CronLineFields]

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255), postable=True, required=True)
    display_name = Field(name="display_name", f_type=String(), postable=True, default_value=name)
    handler = Field(
        name="handler", f_type=ForeignKey(fk_link=HandlerFields), postable=True, required=True
    )
    cluster = Field(
        name="cluster", f_type=ForeignKey(fk_link=ClusterFields), postable=True, required=True
    )
    filesystem = Field(
        name="filesystem", f_type=ForeignKey(fk_link=FileSystemFields), postable=True, required=True
    )
    cron_line = Field(name="cron_line", f_type=ForeignKey(fk_link=CronLineFields), nullable=True)
    config = Field(
        name="config",
        f_type=Json(relates_on=Relation(HandlerFields, HandlerFields.config_schema)),
        dynamic_nullable=True,
        postable=True,
        custom_required=True,
    )
    pid = Field(name="pid", f_type=PositiveInt(), nullable=True)
    state = Field(
        name="state", f_type=Enum(enum_values=["to kill"]), default_value="created", changeable=True
    )
    label = Field(
        name="label", f_type=Enum(enum_values=["on-demand", "cron"]), default_value="on-demand"
    )
    create_date = Field(name="create_date", f_type=DateTime(), default_value=datetime.now())
    start_date = Field(name="start_date", f_type=DateTime(), nullable=True)
    end_date = Field(name="end_date", f_type=DateTime(), nullable=True)


class JobHistoryFields(BaseClass):
    """
    Data type class for
    https://spec.adsw.io/adss_core/adss-97/scheduler.html#job-history
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))
    display_name = Field(name="display_name", f_type=String(), default_value=name)
    handler = Field(name="handler", f_type=ForeignKey(fk_link=HandlerFields))
    cluster = Field(name="cluster", f_type=ForeignKey(fk_link=ClusterFields))
    filesystem = Field(name="filesystem", f_type=ForeignKey(fk_link=FileSystemFields))
    cron_line = Field(name="cron_line", f_type=ForeignKey(fk_link=CronLineFields), nullable=True)
    config = Field(
        name="config",
        f_type=Json(relates_on=Relation(HandlerFields, HandlerFields.config_schema)),
        nullable=True,
        custom_required=True,
    )
    pid = Field(name="pid", f_type=PositiveInt(), nullable=True)
    state = Field(name="state", f_type=Enum(enum_values=["to kill"]), default_value="created")
    label = Field(name="label", f_type=Enum(enum_values=["on-demand", "cron"]))
    create_date = Field(name="create_date", f_type=DateTime())
    start_date = Field(name="start_date", f_type=DateTime(), nullable=True)
    end_date = Field(name="end_date", f_type=DateTime(), nullable=True)
