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

"""Data class synchronization functions"""

import random
from copy import deepcopy

# pylint: disable=import-outside-toplevel
from typing import Tuple


def sync_object_and_role(adcm, fields: dict) -> dict:
    """Sync `object` and `role` fields in Policy data"""
    from tests.api.testdata.getters import get_endpoint_data
    from tests.api.utils.endpoints import Endpoints

    if 'role' not in fields or 'object' not in fields:
        return fields

    new_fields = deepcopy(fields)
    role_id = new_fields['role']['id']
    role = next(filter(lambda r: r['id'] == role_id, get_endpoint_data(adcm, Endpoints.RbacAnyRole)), None)
    if role is None:
        return new_fields

    new_fields['object'] = []
    for object_type in role['parametrized_by_type']:
        role_object = random.choice(get_endpoint_data(adcm=adcm, endpoint=Endpoints[object_type.capitalize()]))
        new_fields["object"].append(
            {
                'id': role_object["id"],
                'name': role_object.get("name", role_object.get("fqdn")),
                'type': object_type,
            }
        )

    return new_fields


def sync_child_roles_hierarchy(adcm, fields: dict):
    """Child roles can be only in infrastructure or application hierarchy"""
    from tests.api.testdata.getters import get_endpoint_data
    from tests.api.utils.endpoints import Endpoints

    if "child" not in fields:
        return fields

    child_list = fields.get("child")

    if not child_list or len(child_list) == 1:
        return fields

    def _role_by_id(roles, role_id):
        return next(filter(lambda x: role_id == x["id"], roles))

    def _has_correct_parametrization(role, allowed_parametrization: Tuple[str]):
        types = _role_by_id(all_roles, role["id"])["parametrized_by_type"]
        return all(role_type in allowed_parametrization for role_type in types)

    all_roles = get_endpoint_data(adcm, endpoint=Endpoints.RbacBusinessRole)
    for role in child_list:
        role_obj = _role_by_id(all_roles, role["id"])
        if parametrization := role_obj["parametrized_by_type"]:
            first_parametrized_child = parametrization
            break
    else:
        # none of children is parametrized, so we don't want to filter children
        return fields

    # "host" is in both hierarchies, so we want infrastructure bundle only in provider case
    is_infrastructure = "provider" in first_parametrized_child
    param_tuple = ("provider", "host") if is_infrastructure else ("cluster", "service", "component")
    fields["child"] = list(filter(lambda x: _has_correct_parametrization(x, param_tuple), child_list))
    return fields
