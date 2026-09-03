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
from collections.abc import Collection
from typing import Final

from core.concern.repo import ConcernDistribution, ConcernRepoI
from core.concern.types import ConcernDraft, ConcernRelatedObjects
from core.types import ADCMCoreType, ClusterDesc, ConcernID, HostDesc
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from cm.converters import core_type_to_model
from cm.models import ConcernItem, ConcernType

# Name of an object may be stored only in the placeholder describing concern's own owner:
# all the other placeholders point at a prototype, an action or a job,
# so they are named after those and are unaffected by rename of an object.
# Owner is described by `source` in every concern but a lock, where it is described by `target`.
_OWNER_PLACEHOLDER: Final = f"(CASE WHEN concern.type = '{ConcernType.LOCK}' THEN 'target' ELSE 'source' END)"

_RENAME_OWNER_IN_PLACEHOLDERS: Final = f"""
UPDATE {ConcernItem._meta.db_table} AS concern
SET reason = jsonb_set(
        concern.reason,
        ARRAY['placeholder', {_OWNER_PLACEHOLDER}, 'name'],
        to_jsonb(%(new_name)s::text)
    )
WHERE concern.owner_id = %(owner_id)s
  AND concern.owner_type_id = %(owner_type_id)s
  AND concern.reason -> 'placeholder' -> {_OWNER_PLACEHOLDER} ->> 'name' = %(previous_name)s
RETURNING concern.id
"""  # noqa: S608


class ConcernRepo(ConcernRepoI):
    def create(self, draft: ConcernDraft) -> ConcernID:
        owner_model = core_type_to_model(core_type=draft.owner.type)

        concern = ConcernItem.objects.create(
            type=draft.type.value,
            cause=draft.cause.value,
            name=draft.name,
            reason=draft.reason,
            blocking=draft.blocking,
            owner_id=draft.owner.id,
            owner_type=ContentType.objects.get_for_model(owner_model),
        )

        return concern.pk

    def link(self, *, concern_id: ConcernID, targets: ConcernRelatedObjects) -> None:
        # NOTE: duplicated from `cm.legacy.services.concern.distribution._add_concern_links_to_objects_in_db`,
        # to be reconciled once concern distribution itself is reworked
        for core_type, ids in targets.items():
            orm_model = core_type_to_model(core_type)
            id_field = f"{orm_model.__name__.lower()}_id"
            m2m_model = orm_model.concerns.through

            m2m_model.objects.bulk_create(
                objs=(m2m_model(concernitem_id=concern_id, **{id_field: object_id}) for object_id in ids),
                ignore_conflicts=True,
            )

    def update_object_name_in_concerns(
        self, object_: ClusterDesc | HostDesc, previous_name: str, new_name: str
    ) -> tuple[ConcernID, ...]:
        owner_type = core_type_to_model(core_type=object_.type).class_content_type

        with connection.cursor() as cursor:
            cursor.execute(
                _RENAME_OWNER_IN_PLACEHOLDERS,
                {
                    "owner_id": object_.id,
                    "owner_type_id": owner_type.id,
                    "previous_name": previous_name,
                    "new_name": new_name,
                },
            )

            return tuple(id_ for (id_,) in cursor.fetchall())

    def get_concerns_distribution(self, concern_ids: Collection[ConcernID]) -> ConcernDistribution:
        distribution: ConcernDistribution = defaultdict(lambda: defaultdict(set))
        if not concern_ids:
            return distribution

        for core_type in ADCMCoreType:
            model = core_type_to_model(core_type=core_type)
            id_field = f"{model.__name__.lower()}_id"

            for object_id, concern_id in model.concerns.through.objects.filter(
                concernitem_id__in=concern_ids
            ).values_list(id_field, "concernitem_id"):
                distribution[core_type][object_id].add(concern_id)

        return distribution
