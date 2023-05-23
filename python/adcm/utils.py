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
from typing import Any

from api.utils import process_requires
from cm.adcm_config.ansible import ansible_decrypt
from cm.models import ADCM, ConfigLog, Prototype


def get_obj_type(obj_type: str) -> str:
    if obj_type == "cluster object":
        return "service"
    elif obj_type == "service component":
        return "component"
    elif obj_type == "host provider":
        return "provider"

    return obj_type


def str_remove_non_alnum(value: str) -> str:
    result = "".join(ch.lower().replace(" ", "-") for ch in value if (ch.isalnum() or ch == " "))
    while result.find("--") != -1:
        result = result.replace("--", "-")
    return result


def get_oauth(oauth_key: str) -> tuple[str | None, str | None]:
    adcm = ADCM.objects.filter().first()
    if not adcm:
        return None, None

    config_log = ConfigLog.objects.get(obj_ref=adcm.config, id=adcm.config.current)
    if not config_log:
        return None, None

    if not config_log.config.get(oauth_key):
        return None, None

    if "client_id" not in config_log.config[oauth_key] or "secret" not in config_log.config[oauth_key]:
        return None, None

    secret = config_log.config[oauth_key]["secret"]
    if not secret:
        return None, None

    return (
        config_log.config[oauth_key]["client_id"],
        ansible_decrypt(secret),
    )


def get_yandex_oauth() -> tuple[str, str]:
    return get_oauth(oauth_key="yandex_oauth")


def get_google_oauth() -> tuple[str, str]:
    return get_oauth(oauth_key="google_oauth")


def has_yandex_oauth() -> bool:
    return all(get_yandex_oauth())


def has_google_oauth() -> bool:
    return all(get_google_oauth())


def get_requires(
    prototype: Prototype,
    adding_service: bool = False,
) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
    if not prototype.requires:
        return None

    proto_dict = {}
    proto_dict = process_requires(proto=prototype, comp_dict=proto_dict, adding_service=adding_service)

    out = []

    for service_name, params in proto_dict.items():
        comp_out = []
        service = params["service"]
        for comp_name in params["components"]:
            comp = params["components"][comp_name]
            comp_out.append(
                {
                    "prototype_id": comp.id,
                    "name": comp_name,
                    "display_name": comp.display_name,
                },
            )

        out.append(
            {
                "prototype_id": service.id,
                "name": service_name,
                "display_name": service.display_name,
                "components": comp_out,
            },
        )

    return out
