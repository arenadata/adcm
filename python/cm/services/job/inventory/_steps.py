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

from typing import Iterable

from django.contrib.contenttypes.models import ContentType

from cm.logger import logger
from cm.models import (
    ADCM,
    ADCMEntity,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostProvider,
    ObjectType,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
    get_default_before_upgrade,
)

# FIXME temporal module
#  that contains all major optimization "public-like function" candidates
#  all of them should be moved somewhere else once they're adopted to new reality
#  and this module should be removed


def get_obj_config(obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host) -> dict:
    if obj.config is None:
        return {}

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)

    return process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)


def get_group_config(obj: ADCMEntity, host: Host) -> dict | None:
    group = host.group_config.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)).last()
    group_config = None
    if group:
        conf, attr = group.get_config_and_attr()
        group_config = process_config_and_attr(obj=group, conf=conf, attr=attr)
    return group_config


def get_before_upgrade(obj: ADCMEntity, host: Host | None) -> dict:  # todo make it bulk
    if obj.before_upgrade == get_default_before_upgrade():
        return obj.before_upgrade

    config, group_object = None, None
    config_log = ConfigLog.objects.filter(id=obj.before_upgrade.get("config_id")).first()
    if host is not None:
        group = host.group_config.filter(
            object_id=obj.id, object_type=ContentType.objects.get_for_model(model=obj)
        ).first()

        if group and obj.before_upgrade.get("groups") and group.name in obj.before_upgrade["groups"]:
            config_log = ConfigLog.objects.filter(
                id=obj.before_upgrade["groups"][group.name]["group_config_id"]
            ).first()
            group_object = group

    if config_log:
        if not obj.before_upgrade.get("bundle_id"):
            bundle_id = obj.cluster.before_upgrade["bundle_id"]
        else:
            bundle_id = obj.before_upgrade["bundle_id"]

        obj_prototype = obj.prototype
        try:
            if obj_prototype.type == ObjectType.COMPONENT:
                old_proto = Prototype.objects.get(
                    name=obj_prototype.name, parent__name=obj_prototype.parent.name, bundle_id=bundle_id
                )
            else:
                old_proto = Prototype.objects.get(name=obj_prototype.name, bundle_id=bundle_id, parent=None)

        except Prototype.DoesNotExist:
            logger.info("Can't get old proto for %s. Old bundle id: %s", obj, bundle_id)

        else:
            from cm.adcm_config.config import get_prototype_config

            old_spec, old_flat_spec, _, _ = get_prototype_config(prototype=old_proto)
            config = process_config_and_attr(
                obj=group_object or obj,
                conf=config_log.config,
                attr=config_log.attr,
                spec=old_spec,
                flat_spec=old_flat_spec,
            )

    return {"state": obj.before_upgrade.get("state"), "config": config}


def fix_fields_for_inventory(prototype_configs: Iterable[PrototypeConfig], config: dict) -> None:
    """
    This function is designed to convert fields of map and list types for inventory
    """
    for prototype_config in prototype_configs:
        if prototype_config.type not in {"map", "list"}:
            continue

        name = prototype_config.name
        sub_name = prototype_config.subname

        fix_value = {} if prototype_config.type == "map" else []

        if sub_name and name in config and sub_name in config[name]:
            if config[name][sub_name] is None:
                config[name][sub_name] = fix_value
        else:
            if name in config and config[name] is None:
                config[name] = fix_value


def process_config_and_attr(
    obj: Cluster | ClusterObject | ServiceComponent | HostProvider | Host | GroupConfig,
    conf: dict,
    attr: dict | None = None,
    spec: dict | None = None,
    flat_spec: dict | None = None,
) -> dict:
    from cm.adcm_config.config import get_prototype_config, process_config

    if not spec:
        prototype = obj.object.prototype if isinstance(obj, GroupConfig) else obj.prototype

        spec, flat_spec, _, _ = get_prototype_config(prototype=prototype)

    new_config = process_config(obj=obj, spec=spec, old_conf=conf)
    fix_fields_for_inventory(prototype_configs=flat_spec.values(), config=new_config)

    if attr:
        for key, value in attr.items():
            if "active" in value and not value["active"]:
                new_config[key] = None

    return new_config
