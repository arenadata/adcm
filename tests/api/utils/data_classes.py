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

"""Endpoint data classes definition"""

from abc import ABC
from typing import Callable, List

# there's a local import, but it's not cyclic really
from tests.api.utils.data_synchronization import (  # pylint: disable=cyclic-import
    sync_child_roles_hierarchy_and_unique_name,
    sync_object_and_role,
)
from tests.api.utils.tools import PARAMETRIZED_BY_LIST
from tests.api.utils.types import (
    BackReferenceFK,
    Boolean,
    DateTime,
    Email,
    EmptyList,
    Enum,
    Field,
    ForeignKey,
    ForeignKeyM2M,
    GenericForeignKeyList,
    Json,
    ListOf,
    ObjectForeignKey,
    Password,
    PositiveInt,
    Relation,
    SmallIntegerID,
    String,
    Text,
    Username,
)

AUTO_VALUE = "auto"


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

    # Synchronize data in result dict when API fields has complex dependencies
    # like foreign keys list depends on other field's value (and this value is also fk)
    dependable_fields_sync: Callable


class ClusterFields(BaseClass):
    """
    Data type class for Cluster object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=255))


class ServiceFields(BaseClass):
    """
    Data type class for Service object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=255))


class ComponentFields(BaseClass):
    """
    Data type class for Component object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=255))


class ProviderFields(BaseClass):
    """
    Data type class for Provider object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=255))


class HostFields(BaseClass):
    """
    Data type class for Host object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    fqdn = Field(name="fqdn", f_type=String(max_length=255))


class ObjectConfigFields(BaseClass):
    """
    Data type class for ObjectConfig object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


class GroupConfigFields(BaseClass):
    """
    Data type class for Config Group object
    https://spec.adsw.io/adcm_core/objects.html#group
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    object_type = Field(
        name="object_type",
        f_type=Enum(enum_values=["cluster", "service", "component", "provider"]),
        required=True,
        postable=True,
    )
    object_id = Field(
        name="object_id",
        f_type=ForeignKey(relates_on=Relation(field=object_type)),
        required=True,
        postable=True,
    )
    name = Field(name="name", f_type=String(max_length=1000), required=True, postable=True, changeable=True)
    description = Field(name="description", f_type=Text(), postable=True, changeable=True, default_value="")
    config = Field(
        name="config",
        f_type=ForeignKey(fk_link=ObjectConfigFields),
        default_value=AUTO_VALUE,
    )
    config_id = Field(name="config_id", f_type=PositiveInt(), default_value=AUTO_VALUE, nullable=True)
    host_candidate = Field(
        # Link to host candidates url for this object. Auto-filled when group-config object creates
        # Candidates list depends on ADCM object for which group-config was created.
        name="host_candidate",
        f_type=String(),
        default_value=AUTO_VALUE,
    )
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


class ConfigLogFields(BaseClass):
    """
    Data type class for ConfigLog object
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    date = Field(name="date", f_type=DateTime(), default_value=AUTO_VALUE)
    obj_ref = Field(name="obj_ref", f_type=ForeignKey(fk_link=ObjectConfigFields), required=True, postable=True)
    description = Field(
        name="description",
        f_type=Text(),
        default_value="",
        postable=True,
    )
    config = Field(
        name="config",
        f_type=Json(relates_on=Relation(field=obj_ref)),
        default_value={},
        postable=True,
        required=True,
    )
    attr = Field(
        name="attr",
        f_type=Json(relates_on=Relation(field=obj_ref)),
        default_value={},
        postable=True,
    )
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


# Back-reference from ConfigLogFields
ObjectConfigFields.current = Field(
    name="current",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value=AUTO_VALUE,
)
ObjectConfigFields.previous = Field(
    name="previous",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value=AUTO_VALUE,
)
ObjectConfigFields.history = Field(
    name="history",
    f_type=BackReferenceFK(fk_link=ConfigLogFields),
    default_value=AUTO_VALUE,
)


class GroupConfigHostCandidatesFields(BaseClass):
    """
    Data type class for GroupConfigHostCandidates object
    """

    predefined_dependencies = [GroupConfigFields]

    id = Field(
        name="id",
        f_type=PositiveInt(),
        default_value=AUTO_VALUE,
    )
    cluster_id = Field(name="cluster_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    prototype_id = Field(name="prototype_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    provider_id = Field(name="provider_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    fqdn = Field(name="fqdn", f_type=String(), default_value=AUTO_VALUE)
    description = Field(name="description", f_type=Text(), default_value=AUTO_VALUE)
    state = Field(name="state", f_type=String(), default_value=AUTO_VALUE)
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


class GroupConfigHostsFields(BaseClass):
    """
    Data type class for GroupConfigHostsFields object
    https://spec.adsw.io/adcm_core/objects.html#group-config-hosts
    """

    predefined_dependencies = [GroupConfigFields]

    id = Field(
        name="id",
        f_type=ForeignKey(fk_link=GroupConfigHostCandidatesFields),
        required=True,
        postable=True,
    )
    cluster_id = Field(name="cluster_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    bundle_id = Field(name="bundle_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    prototype_id = Field(name="prototype_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    maintenance_mode = Field(name="maintenance_mode", f_type=String(), default_value=AUTO_VALUE)
    provider_id = Field(name="provider_id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    fqdn = Field(name="fqdn", f_type=String(), default_value=AUTO_VALUE)
    description = Field(name="description", f_type=Text(), default_value=AUTO_VALUE)
    state = Field(name="state", f_type=String(), default_value=AUTO_VALUE)
    locked = Field(name="locked", f_type=Boolean(), default_value=AUTO_VALUE)
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


# Back-reference from GroupConfigHostsFields
GroupConfigFields.hosts = Field(
    name="hosts",
    f_type=BackReferenceFK(fk_link=GroupConfigHostsFields),
    default_value=AUTO_VALUE,
)


class RbacUserFields(BaseClass):
    """
    Data type class for RbacUser object
    """

    id = Field(
        name="id",
        f_type=PositiveInt(),
        default_value=AUTO_VALUE,
    )
    username = Field(
        name="username", f_type=Username(max_length=150, special_chars="@.+-_"), required=True, postable=True
    )
    first_name = Field(
        name="first_name", default_value="", f_type=String(max_length=150), postable=True, changeable=True
    )
    last_name = Field(name="last_name", default_value="", f_type=String(max_length=150), postable=True, changeable=True)
    email = Field(name="email", default_value="", f_type=Email(), postable=True, changeable=True)
    password = Field(name="password", f_type=Password(), required=True, postable=True, changeable=True)
    is_superuser = Field(name="is_superuser", f_type=Boolean(), default_value=False, postable=True, changeable=True)
    profile = Field(name="profile", f_type=Json(), default_value="", postable=True, changeable=True)
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)
    built_in = Field(name="built_in", f_type=Boolean(), default_value=AUTO_VALUE)
    type = Field(name="type", f_type=String(max_length=16), default_value=AUTO_VALUE)
    is_active = Field(name="is_active", f_type=Boolean(), default_value=True)


class RbacGroupFields(BaseClass):
    """
    Data type class for RbacGroup object
    """

    id = Field(
        name="id",
        f_type=PositiveInt(),
        default_value=AUTO_VALUE,
    )
    user = Field(
        name="user", f_type=ForeignKeyM2M(fk_link=RbacUserFields), postable=True, changeable=True, default_value=[]
    )
    name = Field(name="name", f_type=String(max_length=100), required=True, postable=True, changeable=True)
    description = Field(name="description", f_type=Text(), postable=True, changeable=True, default_value="")
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)
    built_in = Field(name="built_in", f_type=Boolean(), default_value=AUTO_VALUE)
    type = Field(name="type", f_type=String(max_length=16), default_value=AUTO_VALUE)


RbacUserFields.group = Field(
    name="group", f_type=ForeignKeyM2M(fk_link=RbacGroupFields), postable=True, changeable=True, default_value=[]
)


class RbacSimpleRoleFields(BaseClass):
    """
    Data type class for RbacSimpleRoleFields (type='role').
    Used for Role creation only
    """

    dependable_fields_sync = sync_child_roles_hierarchy_and_unique_name

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    # default_value="auto" because we can't change name after it's set
    # it's "not postable", because we can only set this field during creation, not change it after
    # and currently framework can't resolve it correctly
    name = Field(name="name", f_type=String(max_length=160), default_value=AUTO_VALUE, nullable=True)
    display_name = Field(
        name="display_name",
        f_type=String(max_length=160),
        default_value="",
        required=True,
        postable=True,
        changeable=True,
    )
    description = Field(name="description", f_type=Text(), default_value="", postable=True, changeable=True)
    built_in = Field(name="built_in", f_type=Boolean(), default_value=False)
    # type is actually changeable=True and postable=True, but now it's only value
    # (since it's shouldn't be 'hidden' or 'business') is 'role', so we can't actually change it
    type = Field(name="type", f_type=String(), default_value="role")
    # category is a list of FK to a "ProductCategory" that is hard to get from API
    category = Field(name="category", f_type=ListOf(SmallIntegerID(max_value=2)), default_value=[])
    parametrized_by_type = Field(
        name="parametrized_by_type", f_type=ListOf(Enum(PARAMETRIZED_BY_LIST)), default_value=AUTO_VALUE
    )

    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)
    any_category = Field(name="any_category", f_type=Boolean(), default_value=False)


class RbacBuiltInRoleFields(BaseClass):
    """
    Data type class for RbacBuiltinRoleFields
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=160), nullable=True)
    display_name = Field(
        name="display_name",
        f_type=String(max_length=160),
        default_value="",
        required=True,
        postable=True,
        changeable=True,
    )
    description = Field(name="description", f_type=Text(), default_value="")

    category = Field(name="category", f_type=ListOf(SmallIntegerID(max_value=1)), default_value=[])
    parametrized_by_type = Field(
        name="parametrized_by_type", f_type=ListOf(Enum(PARAMETRIZED_BY_LIST)), default_value=AUTO_VALUE
    )
    built_in = Field(name="built_in", f_type=Boolean(), default_value=True)
    type = Field(name="type", f_type=Enum(["role", "business", "hidden"]), default_value="role")
    child = Field(name="child", f_type=EmptyList(), default_value=[])
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)
    any_category = Field(name="any_category", f_type=Boolean(), default_value=False)


class RbacBusinessRoleFields(RbacBuiltInRoleFields):
    """Technical BaseClass for getting only business roles"""


RbacSimpleRoleFields.child = Field(
    name="child", f_type=ForeignKeyM2M(fk_link=RbacBusinessRoleFields), postable=True, changeable=True, required=True
)


class RbacNotBuiltInPolicyFields(BaseClass):
    """
    Data type class for RbacPolicyFields objects
    """

    dependable_fields_sync = sync_object_and_role

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=160), postable=True, required=True, changeable=True)
    description = Field(name="description", f_type=Text(), default_value="", postable=True, changeable=True)
    role = Field(
        name="role", f_type=ObjectForeignKey(RbacSimpleRoleFields), required=True, postable=True, changeable=True
    )
    built_in = Field(name="built_in", f_type=Boolean(), default_value=False)
    # actually this field isn't required when role isn't parametrized
    object = Field(
        name="object",
        f_type=GenericForeignKeyList(relates_on=Relation(field=role)),
        required=True,
        postable=True,
        changeable=True,
        default_value=[],
    )
    user = Field(
        name="user",
        f_type=ForeignKeyM2M(fk_link=RbacUserFields),
        default_value=[],
        postable=True,
        changeable=True,
        custom_required=True,
    )
    group = Field(
        name="group",
        f_type=ForeignKeyM2M(fk_link=RbacGroupFields),
        default_value=[],
        postable=True,
        changeable=True,
        custom_required=True,
    )
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)


class RbacBuiltInPolicyFields(BaseClass):
    """
    Data type class for RbacBuiltInPolicyFields.

    Note: we can't truly create built_in roles
    """

    id = Field(name="id", f_type=PositiveInt(), default_value=AUTO_VALUE)
    name = Field(name="name", f_type=String(max_length=160), required=True, postable=True, changeable=True)
    description = Field(name="description", f_type=Text(), default_value="", postable=True, changeable=True)
    role = Field(name="role", f_type=ObjectForeignKey(RbacSimpleRoleFields), required=True, postable=True)
    built_in = Field(name="built_in", f_type=Boolean(), default_value=True)
    # actually this field isn't required when role isn't parametrized
    object = Field(
        name="object",
        f_type=GenericForeignKeyList(relates_on=Relation(field=role)),
        required=True,
        postable=True,
        default_value=[],
    )
    # user or group should be not empty
    user = Field(name="user", f_type=ForeignKeyM2M(fk_link=RbacUserFields), required=True, postable=True)
    group = Field(name="group", f_type=ForeignKeyM2M(fk_link=RbacGroupFields), default_value=[], postable=True)
    url = Field(name="url", f_type=String(), default_value=AUTO_VALUE)
