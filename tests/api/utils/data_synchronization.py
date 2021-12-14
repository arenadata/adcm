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


def sync_object_and_role(adcm, fields: dict) -> dict:
    """Sync `object` and `role` fields in Policy data"""
    from tests.api.utils.endpoints import Endpoints
    from tests.api.testdata.getters import get_endpoint_data

    if 'role' not in fields or 'object' not in fields:
        return fields

    new_fields = deepcopy(fields)
    role_id = new_fields['role']['id']
    role = next(filter(lambda r: r['id'] == role_id, get_endpoint_data(adcm, Endpoints.RbacAnyRole)), None)
    if role is None:
        return new_fields

    new_fields['object'] = [
        {
            'id': random.choice(get_endpoint_data(adcm=adcm, endpoint=Endpoints[object_type.capitalize()]))["id"],
            'type': object_type,
        }
        for object_type in role['parametrized_by_type']
    ]
    return new_fields
