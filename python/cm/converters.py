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

from typing import TypeAlias

from audit.models import AuditObjectType
from core.types import ADCMCoreType, ADCMHostGroupType, CoreObjectDescriptor, ExtraActionTargetType
from django.db.models import Model

from cm.models import ADCM, ActionHostGroup, Cluster, ClusterObject, GroupConfig, Host, HostProvider, ServiceComponent

CoreObject: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host
GroupObject: TypeAlias = GroupConfig | ActionHostGroup


def core_type_to_model(core_type: ADCMCoreType) -> type[CoreObject | ADCM]:
    match core_type:
        case ADCMCoreType.CLUSTER:
            return Cluster
        case ADCMCoreType.SERVICE:
            return ClusterObject
        case ADCMCoreType.COMPONENT:
            return ServiceComponent
        case ADCMCoreType.HOSTPROVIDER:
            return HostProvider
        case ADCMCoreType.HOST:
            return Host
        case ADCMCoreType.ADCM:
            return ADCM
        case _:
            raise ValueError(f"Can't convert {core_type} to ORM model")


def host_group_type_to_model(host_group_type: ADCMHostGroupType) -> type[GroupObject]:
    if host_group_type == ADCMHostGroupType.CONFIG:
        return GroupConfig

    if host_group_type == ADCMHostGroupType.ACTION:
        return ActionHostGroup

    raise ValueError(f"Can't convert {host_group_type} to ORM model")


def core_type_to_db_record_type(core_type: ADCMCoreType) -> str:
    match core_type:
        case ADCMCoreType.CLUSTER:
            return "cluster"
        case ADCMCoreType.SERVICE:
            return "service"
        case ADCMCoreType.COMPONENT:
            return "component"
        case ADCMCoreType.HOSTPROVIDER:
            return "provider"
        case ADCMCoreType.HOST:
            return "host"
        case ADCMCoreType.ADCM:
            return "adcm"
        case _:
            raise ValueError(f"Can't convert {core_type} to type name in DB")


def db_record_type_to_core_type(db_record_type: str) -> ADCMCoreType:
    try:
        return ADCMCoreType(db_record_type)
    except ValueError:
        if db_record_type == "provider":
            return ADCMCoreType.HOSTPROVIDER

        raise


def model_name_to_core_type(model_name: str) -> ADCMCoreType:
    name_ = model_name.lower()
    try:
        return ADCMCoreType(name_)
    except ValueError:
        if name_ == "clusterobject":
            return ADCMCoreType.SERVICE

        if name_ == "servicecomponent":
            return ADCMCoreType.COMPONENT

        raise


def model_to_core_type(model: type[Model]) -> ADCMCoreType:
    return model_name_to_core_type(model_name=model.__name__)


def orm_object_to_core_type(object_: ADCM | CoreObject) -> ADCMCoreType:
    return model_to_core_type(model=object_.__class__)


def orm_object_to_core_descriptor(object_: ADCM | CoreObject) -> CoreObjectDescriptor:
    return CoreObjectDescriptor(id=object_.pk, type=orm_object_to_core_type(object_))


def model_to_action_target_type(model: type[Model]) -> ADCMCoreType | ExtraActionTargetType:
    if model == ActionHostGroup:
        return ExtraActionTargetType.ACTION_HOST_GROUP

    return model_to_core_type(model=model)


def orm_object_to_action_target_type(
    object_: ADCM | CoreObject | ActionHostGroup,
) -> ADCMCoreType | ExtraActionTargetType:
    return model_to_action_target_type(model=object_.__class__)


def model_name_to_audit_object_type(model_name: str) -> AuditObjectType:
    # model_name is `model` field from ContentType model or str(<Model>).lower()
    audit_object_type = _model_name_to_audit_object_type_map.get(model_name)

    if audit_object_type is None:
        raise ValueError(f"Can't convert {model_name} to audit object type")

    return audit_object_type


_model_name_to_audit_object_type_map = {
    "cluster": AuditObjectType.CLUSTER,
    "clusterobject": AuditObjectType.SERVICE,
    "servicecomponent": AuditObjectType.COMPONENT,
    "host": AuditObjectType.HOST,
    "hostprovider": AuditObjectType.PROVIDER,
    "bundle": AuditObjectType.BUNDLE,
    "prototype": AuditObjectType.PROTOTYPE,
    "adcm": AuditObjectType.ADCM,
    "user": AuditObjectType.USER,
    "group": AuditObjectType.GROUP,
    "role": AuditObjectType.ROLE,
    "policy": AuditObjectType.POLICY,
    "actionhostgroup": AuditObjectType.ACTION_HOST_GROUP,
}
