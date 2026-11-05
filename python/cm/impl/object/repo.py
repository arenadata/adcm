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

from collections.abc import Collection
import json

from core.object.repo import ObjectRepoI
from core.types import ADCMCoreType, Descriptor
from django.db import connection

from cm.converters import core_type_to_model


class ObjectRepo(ObjectRepoI):
    def set_state(self, object_: Descriptor[ADCMCoreType], state: str) -> None:
        core_type_to_model(core_type=object_.type).objects.filter(id=object_.id).update(state=state)

    def update_multi_state(
        self, object_: Descriptor[ADCMCoreType], add: Collection[str], remove: Collection[str]
    ) -> list[str]:
        if not add and not remove:
            return self.retrieve_multi_state(object_=object_)

        model = core_type_to_model(core_type=object_.type)
        expression_sql, expression_params = _multi_state_update_expression(add=add, remove=remove)

        sql = f'UPDATE "{model._meta.db_table}" SET multi_state = {expression_sql} WHERE id = %s RETURNING multi_state'  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(sql, [*expression_params, object_.id])
            multi_state: dict = json.loads(cursor.fetchone()[0])

        return sorted(multi_state)

    def retrieve_multi_state(self, object_: Descriptor[ADCMCoreType]) -> list[str]:
        multi_state: dict = (
            core_type_to_model(core_type=object_.type).objects.values_list("_multi_state", flat=True).get(id=object_.id)
        )
        return sorted(multi_state)


def _multi_state_update_expression(*, add: Collection[str], remove: Collection[str]) -> tuple[str, list]:
    # `_multi_state` is stored in the `multi_state` column as a JSON object `{flag: 1}`.
    # JSONB operators are applied in a single UPDATE, so sibling changes can't clobber each other:
    # `||` merges new flags, `-` removes flags. All user values are passed as parameters.
    sql = "multi_state"
    params: list = []

    if add:
        sql = f"{sql} || %s::jsonb"
        params.append(json.dumps(dict.fromkeys(add, 1)))

    if remove:
        sql = f"({sql}) - %s::text[]"
        params.append(list(remove))

    return sql, params
