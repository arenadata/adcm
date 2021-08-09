"""Endpoint data classes definition"""
# pylint: disable=too-few-public-methods

from abc import ABC
from typing import List

from .types import (
    Field,
    PositiveInt,
    String,
    Text,
    Json,
    Enum,
    ForeignKey,
    BackReferenceFK,
    DateTime, Relation,
)


class BaseClass(ABC):
    """Base data class"""

    # List of BaseClass that are NOT included in POST method for current Class
    # but should exist before data preparation
    # and creation of current object
    predefined_dependencies: List["BaseClass"] = []

    # List of BaseClass that are NOT included in POST method for current Class
    # and should be generated implicitly after data preparation
    # and creation of current object
    implicitly_depends_on: List["BaseClass"] = []


class ClusterFields(BaseClass):
    """
    Data type class for Cluster object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))


class ServiceFields(BaseClass):
    """
    Data type class for Service object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))


class ComponentFields(BaseClass):
    """
    Data type class for Component object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))


class ProviderFields(BaseClass):
    """
    Data type class for Provider object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    name = Field(name="name", f_type=String(max_length=255))


class HostFields(BaseClass):
    """
    Data type class for Host object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    fqdn = Field(name="fqdn", f_type=String(max_length=255))


class ObjectConfigFields(BaseClass):
    """
    Data type class for ObjectConfig object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    url = Field(name="url", f_type=String(), default_value="auto")


class ConfigGroupFields(BaseClass):
    """
    Data type class for Config Group object
    https://spec.adsw.io/adcm_core/objects.html#group
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    object_type = Field(
        name="object_type",
        f_type=Enum(enum_values=["cluster", "service", "component", "provider"]),
        required=True,
        postable=True
    )
    object_id = Field(
        name="object_id",
        f_type=ForeignKey(relates_on=Relation(field=object_type)),
        required=True,
        postable=True,
    )
    name = Field(
        name="name", f_type=String(max_length=30), required=True, postable=True, changeable=True
    )
    description = Field(
        name="description", f_type=Text(), nullable=True, postable=True, changeable=True
    )
    config = Field(
        name="config", f_type=ForeignKey(fk_link=ObjectConfigFields), nullable=True, changeable=True
    )
    url = Field(name="url", f_type=String(), default_value="auto")


class ConfigLogFields(BaseClass):
    """
    Data type class for ConfigLog object
    """
    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    date = Field(name="date", f_type=DateTime(), default_value="auto")
    obj_ref = Field(
        name="obj_ref", f_type=ForeignKey(fk_link=ObjectConfigFields), required=True, postable=True
    )
    description = Field(
        name="description",
        f_type=Text(),
        default_value="",
        nullable=True,
        postable=True,
    )
    config = Field(
        name="config",
        f_type=Json(relates_on=Relation(field=obj_ref)),
        default_value={},
        postable=True,
    )
    attr = Field(
        name="attr",
        f_type=Json(relates_on=Relation(field=obj_ref)),
        default_value={},
        postable=True
    )
    url = Field(name="url", f_type=String(), default_value="auto")


# Back-reference from ConfigLogFields
ObjectConfigFields.current = Field(
    name="current",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value="auto",
)
ObjectConfigFields.previous = Field(
    name="previous",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value="auto",
)
ObjectConfigFields.history = Field(
    name="history",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value="auto",
)


class HostGroupFields(BaseClass):
    """
    Data type class for Host Group object
    https://spec.adsw.io/adcm_core/objects.html#group
    """

    id = Field(name="id", f_type=PositiveInt(), default_value="auto")
    host = Field(
        name="host",
        f_type=ForeignKey(fk_link=HostFields),
        required=True,
        postable=True,
        changeable=True
    )
    group = Field(
        name="group",
        f_type=ForeignKey(fk_link=ConfigGroupFields),
        required=True,
        postable=True,
        changeable=True
    )
    url = Field(name="url", f_type=String(), default_value="auto")


# Back-reference from HostGroupFields
ConfigGroupFields.hosts = Field(
    name="hosts",
    f_type=BackReferenceFK(fk_link=HostGroupFields),
    default_value="auto",
    nullable=True
)
