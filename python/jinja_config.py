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

from pathlib import Path
from typing import Literal, TypedDict

from cm.models import (
    Action,
    ADCMEntity,
    Cluster,
    ClusterObject,
    Host,
    ObjectType,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
)
from cm.services.bundle import BundlePathResolver, detect_relative_path_to_bundle_root
from cm.services.cluster import retrieve_clusters_topology
from cm.services.config.patterns import Pattern
from cm.services.job.inventory import get_cluster_vars
from django.conf import settings
from jinja2 import Template
from yaml import load, safe_load
from yaml.loader import SafeLoader


class ActionContext(TypedDict):
    owner_group: str
    name: str


def _get_attr(config: dict) -> dict:
    attr = {}

    if all(
        (
            "activatable" in config["limits"],
            "active" in config["limits"],
            config["type"] == "group",
            config.get("name"),
        ),
    ):
        attr[config["name"]] = config["limits"]

    return attr


def _get_limits(config: dict, root_path: Path) -> dict:
    limits = {}

    if "pattern" in config:
        if config["type"] not in ("string", "text", "password", "secrettext"):
            message = f"Incorrectly rendered `config_jinja` file. `pattern` is not allowed in {config['type']}"
            raise RuntimeError(message)

        pattern = Pattern(regex_pattern=config.pop("pattern"))
        if not pattern.is_valid:
            display_name = config.get("display_name", config["name"])
            message = f"The pattern attribute value of {display_name} config parameter is not valid regular expression"
            raise RuntimeError(message)

        default = config.get("default")
        if default is not None and not pattern.matches(str(default)):
            display_name = config.get("display_name", config["name"])
            message = f"Default attribute value of {display_name} config parameter does not match pattern"
            raise RuntimeError(message)

        limits["pattern"] = pattern.raw

    if "yspec" in config and config["type"] in settings.STACK_COMPLEX_FIELD_TYPES:
        limits["yspec"] = safe_load(stream=(root_path / config["yspec"]).read_text(encoding="utf-8"))

    if "option" in config and config["type"] == "option":
        limits["option"] = config["option"]

    if "source" in config and config["type"] == "variant":
        variant_type = config["source"]["type"]
        source = {"type": variant_type, "args": None}

        source["strict"] = config["source"].get("strict", True)

        if variant_type == "inline":
            source["value"] = config["source"]["value"]
        elif variant_type in ("config", "builtin"):
            source["name"] = config["source"]["name"]

        if variant_type == "builtin" and "args" in config["source"]:
            source["args"] = config["source"]["args"]

        limits["source"] = source

    if "activatable" in config and config["type"] == "group":
        limits.update(
            activatable=config["activatable"],
            active=False,
        )

        if "active" in config:
            limits.update(active=config["active"])

    if config["type"] in settings.STACK_NUMERIC_FIELD_TYPES:
        if "min" in config:
            limits["min"] = config["min"]

        if "max" in config:
            limits["max"] = config["max"]

    for label in ("read_only", "writable"):
        if label in config:
            limits[label] = config[label]

    return limits


def _normalize_config(config: dict, root_path: Path, name: str = "", subname: str = "") -> list[dict]:
    config_list = [config]

    name = name or config["name"]
    config["name"] = name
    if subname:
        config["subname"] = subname

    if config.get("display_name") is None:
        config["display_name"] = subname or name

    config["limits"] = _get_limits(config=config, root_path=root_path)

    if config["type"] in settings.STACK_FILE_FIELD_TYPES and config.get("default"):
        config["default"] = detect_relative_path_to_bundle_root(source_file_dir=root_path, raw_path=config["default"])

    if "subs" in config:
        for subconf in config["subs"]:
            config_list.extend(
                _normalize_config(config=subconf, root_path=root_path, name=name, subname=subconf["name"]),
            )

    for field in settings.TEMPLATE_CONFIG_DELETE_FIELDS:
        if field in config:
            del config[field]

    return config_list


def get_action_info(action: Action) -> dict[Literal["action"], ActionContext]:
    owner_prototype = action.prototype

    if owner_prototype.type == ObjectType.SERVICE:
        owner_group = owner_prototype.name
    elif owner_prototype.type == ObjectType.COMPONENT:
        parent_name = Prototype.objects.values_list("name", flat=True).get(id=owner_prototype.parent_id)
        owner_group = f"{parent_name}.{owner_prototype}"
    else:
        owner_group = owner_prototype.type.upper()

    return {"action": ActionContext(name=action.name, owner_group=owner_group)}


def get_jinja_config(action: Action, obj: ADCMEntity) -> tuple[list[PrototypeConfig], dict]:
    if isinstance(obj, Cluster):
        cluster_topology = next(retrieve_clusters_topology([obj.pk]))
    elif isinstance(obj, (ClusterObject, ServiceComponent, Host)) and obj.cluster_id:
        cluster_topology = next(retrieve_clusters_topology([obj.cluster_id]))
    else:
        message = f"Can't detect cluster variables for {obj}"
        raise RuntimeError(message)

    resolver = BundlePathResolver(bundle_hash=action.prototype.bundle.hash)
    jinja_conf_file = resolver.resolve(action.config_jinja)
    template = Template(source=jinja_conf_file.read_text(encoding="utf-8"))
    data_yaml = template.render(
        **get_cluster_vars(topology=cluster_topology).dict(by_alias=True, exclude_defaults=True),
        **get_action_info(action=action),
    )
    data = load(stream=data_yaml, Loader=SafeLoader)

    configs = []
    attr = {}
    for config in data:
        for normalized_config in _normalize_config(config=config, root_path=jinja_conf_file.parent):
            configs.append(PrototypeConfig(prototype=action.prototype, action=action, **normalized_config))
            attr.update(**_get_attr(config=normalized_config))

    return configs, attr
