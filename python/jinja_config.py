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

from cm.models import Action, ADCMEntity, Cluster, ClusterObject, Host, PrototypeConfig, ServiceComponent
from cm.services.cluster import retrieve_clusters_topology
from cm.services.job.inventory import get_cluster_vars
from django.conf import settings
from jinja2 import Template
from yaml import load, safe_load
from yaml.loader import SafeLoader


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

    if "yspec" in config and config["type"] in settings.STACK_COMPLEX_FIELD_TYPES:
        with Path(root_path, config["yspec"]).open(encoding=settings.ENCODING_UTF_8) as f:
            data = f.read()

        limits["yspec"] = safe_load(stream=data)

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

    if "subs" in config:
        for subconf in config["subs"]:
            config_list.extend(
                _normalize_config(config=subconf, root_path=root_path, name=name, subname=subconf["name"]),
            )

    for field in settings.TEMPLATE_CONFIG_DELETE_FIELDS:
        if field in config:
            del config[field]

    return config_list


def get_jinja_config(action: Action, obj: ADCMEntity) -> tuple[list[PrototypeConfig], dict]:
    if isinstance(obj, Cluster):
        cluster_topology = next(retrieve_clusters_topology([obj.pk]))
    elif isinstance(obj, (ClusterObject, ServiceComponent, Host)) and obj.cluster_id:
        cluster_topology = next(retrieve_clusters_topology([obj.cluster_id]))
    else:
        message = f"Can't detect cluster variables for {obj}"
        raise RuntimeError(message)

    jinja_conf_file = Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, action.config_jinja)
    template = Template(source=jinja_conf_file.read_text(encoding=settings.ENCODING_UTF_8))
    data_yaml = template.render(get_cluster_vars(topology=cluster_topology))
    data = load(stream=data_yaml, Loader=SafeLoader)

    configs = []
    attr = {}
    for config in data:
        for normalized_config in _normalize_config(
            config=config, root_path=Path(settings.BUNDLE_DIR, action.prototype.bundle.hash, action.prototype.path)
        ):
            configs.append(PrototypeConfig(prototype=action.prototype, action=action, **normalized_config))
            attr.update(**_get_attr(config=normalized_config))

    return configs, attr
