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
from collections import defaultdict
from hashlib import sha256
from itertools import compress
from typing import Iterable, Iterator, List, Literal
import json

from adcm.permissions import RUN_ACTION_PERM_PREFIX
from cm.adcm_config.config import get_default
from cm.models import (
    Action,
    ADCMEntity,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    PrototypeConfig,
    ServiceComponent,
)
from django.conf import settings
from jinja_config import get_jinja_config
from rbac.models import User

from api_v2.config.utils import convert_attr_to_adcm_meta, get_config_schema


def get_str_hash(value: str) -> str:
    return sha256(value.encode(settings.ENCODING_UTF_8)).hexdigest()


def get_run_actions_permissions(actions: Iterable[Action]) -> list[str]:
    return [f"{RUN_ACTION_PERM_PREFIX}{get_str_hash(value=action.name)}" for action in actions]


def filter_actions_by_user_perm(user: User, obj: ADCMEntity, actions: Iterable[Action]) -> Iterator[Action]:
    mask = [user.has_perm(perm=perm, obj=obj) for perm in get_run_actions_permissions(actions=actions)]

    return compress(data=actions, selectors=mask)


def check_run_perms(user: User, action: Action, obj: ADCMEntity) -> bool:
    return user.has_perm(perm=f"{RUN_ACTION_PERM_PREFIX}{get_str_hash(value=action.name)}", obj=obj)


def unique_hc_entries(
    hc_create_data: list[dict[Literal["host_id", "component_id"], int]],
) -> list[dict[Literal["host_id", "component_id"], int]]:
    return [
        {"host_id": host_id, "component_id": component_id}
        for host_id, component_id in {(entry["host_id"], entry["component_id"]) for entry in hc_create_data}
    ]


def insert_service_ids(
    hc_create_data: List[dict[Literal["host_id", "component_id"], int]],
) -> List[dict[Literal["host_id", "component_id", "service_id"], int]]:
    component_ids = {single_hc["component_id"] for single_hc in hc_create_data}
    component_service_map = {
        component.pk: component.service_id for component in ServiceComponent.objects.filter(pk__in=component_ids)
    }

    for single_hc in hc_create_data:
        single_hc["service_id"] = component_service_map[single_hc["component_id"]]

    return hc_create_data


def get_action_configuration(
    action_: Action, object_: Cluster | ClusterObject | ServiceComponent | HostProvider | Host
) -> tuple[dict | None, dict | None, dict | None]:
    if action_.config_jinja:
        prototype_configs, _ = get_jinja_config(action=action_, obj=object_)
    else:
        prototype_configs = PrototypeConfig.objects.filter(prototype=action_.prototype, action=action_).order_by("id")

    if not prototype_configs:
        return None, None, None

    config = defaultdict(dict)
    attr = {}

    for prototype_config in prototype_configs:
        name = prototype_config.name
        sub_name = prototype_config.subname

        if prototype_config.type == "group":
            if "activatable" in prototype_config.limits:
                attr[name] = {"active": prototype_config.limits["active"]}

            continue

        value = get_default(conf=prototype_config, prototype=action_.prototype)

        if prototype_config.type == "json":
            value = json.dumps(value) if value is not None else None

        if sub_name:
            config[name][sub_name] = value
        else:
            config[name] = value

    config_schema = get_config_schema(object_=object_, prototype_configs=prototype_configs)
    adcm_meta = convert_attr_to_adcm_meta(attr=attr)

    return config_schema, config, adcm_meta
