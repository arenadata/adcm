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

from collections.abc import Collection, Iterable
from typing import Final, cast
import json

from core.object.repo import ObjectRepoI
from core.object.types import Selector, SelectorOwnerDescriptor, SelectorTargetDescriptor
from core.types import ADCMCoreType, ADCMHostGroupType, CoreObjectDescriptor, Descriptor, HostID
from django.db import connection
from django.db.models import F, QuerySet, Value

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import ActionHostGroup, Cluster, Component, Host, Provider, Service

_SELECTOR_FIELDS_MAP: Final = {
    Cluster: {
        "object_id": F("id"),
        "object_name": F("name"),
        "type_name": Value(ADCMCoreType.CLUSTER.value),
    },
    Service: {
        "object_id": F("id"),
        "object_name": F("prototype__display_name"),
        "type_name": Value(ADCMCoreType.SERVICE.value),
    },
    Component: {
        "object_id": F("id"),
        "object_name": F("prototype__display_name"),
        "type_name": Value(ADCMCoreType.COMPONENT.value),
    },
    Host: {
        "object_id": F("id"),
        "object_name": F("fqdn"),
        "type_name": Value(ADCMCoreType.HOST.value),
    },
    Provider: {
        "object_id": F("id"),
        "object_name": F("name"),
        "type_name": Value(ADCMCoreType.PROVIDER.value),
    },
}


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

    def build_selector(
        self,
        targets: Iterable[SelectorTargetDescriptor],
        owner: SelectorOwnerDescriptor | None = None,
    ) -> dict[SelectorTargetDescriptor, Selector]:
        return _build_selectors(targets=targets, owner=owner)


# Selector
def _build_selectors(
    targets: Iterable[SelectorTargetDescriptor],
    owner: SelectorOwnerDescriptor | None,
) -> dict[SelectorTargetDescriptor, Selector]:
    target_list = list(targets)
    if owner is not None:
        return {target: _build_selector_single(target=target, owner=owner) for target in target_list}

    selectors: dict[SelectorTargetDescriptor, Selector] = {}

    grouped: dict[ADCMCoreType | ADCMHostGroupType, list[SelectorTargetDescriptor]] = {}
    for target in target_list:
        grouped.setdefault(target.type, []).append(target)

    for target_type, entries in grouped.items():
        ids = [target.id for target in entries]

        match target_type:
            case ADCMCoreType.ADCM:
                for target in entries:
                    selectors[target] = {ADCMCoreType.ADCM: {"id": target.id, "name": "adcm"}}

            case ADCMHostGroupType.ACTION:
                # Not batched: each action host group resolves its owner with separate queries,
                # so the number of queries grows with the number of action host groups (N+1).
                # Such a selector is only built for tasks on an action host group, and there are
                # no real requests for selectors of many action host groups at once.
                for target in entries:
                    selectors[target] = _build_selector_single(target=target)

            case ADCMCoreType.CLUSTER:
                name_by_id = dict(Cluster.objects.filter(id__in=ids).values_list("id", "name"))
                for target in entries:
                    selectors[target] = {ADCMCoreType.CLUSTER: {"id": target.id, "name": name_by_id[target.id]}}

            case ADCMCoreType.PROVIDER:
                name_by_id = dict(Provider.objects.filter(id__in=ids).values_list("id", "name"))
                for target in entries:
                    selectors[target] = {ADCMCoreType.PROVIDER: {"id": target.id, "name": name_by_id[target.id]}}

            case ADCMCoreType.SERVICE:
                service_by_id = {
                    row["id"]: row
                    for row in Service.objects.filter(id__in=ids).values("id", "prototype__display_name", "cluster_id")
                }
                cluster_name_by_id = dict(
                    Cluster.objects.filter(id__in={row["cluster_id"] for row in service_by_id.values()}).values_list(
                        "id", "name"
                    )
                )
                for target in entries:
                    row = service_by_id[target.id]
                    selectors[target] = {
                        ADCMCoreType.SERVICE: {"id": target.id, "name": row["prototype__display_name"]},
                        ADCMCoreType.CLUSTER: {
                            "id": row["cluster_id"],
                            "name": cluster_name_by_id[row["cluster_id"]],
                        },
                    }

            case ADCMCoreType.COMPONENT:
                component_by_id = {
                    row["id"]: row
                    for row in Component.objects.filter(id__in=ids).values(
                        "id", "prototype__display_name", "cluster_id", "service_id"
                    )
                }
                service_name_by_id = dict(
                    Service.objects.filter(id__in={row["service_id"] for row in component_by_id.values()}).values_list(
                        "id", "prototype__display_name"
                    )
                )
                cluster_name_by_id = dict(
                    Cluster.objects.filter(id__in={row["cluster_id"] for row in component_by_id.values()}).values_list(
                        "id", "name"
                    )
                )
                for target in entries:
                    row = component_by_id[target.id]
                    selectors[target] = {
                        ADCMCoreType.COMPONENT: {"id": target.id, "name": row["prototype__display_name"]},
                        ADCMCoreType.SERVICE: {
                            "id": row["service_id"],
                            "name": service_name_by_id[row["service_id"]],
                        },
                        ADCMCoreType.CLUSTER: {
                            "id": row["cluster_id"],
                            "name": cluster_name_by_id[row["cluster_id"]],
                        },
                    }

            case ADCMCoreType.HOST:
                host_by_id = {
                    host_id: (fqdn, provider_id)
                    for host_id, fqdn, provider_id in Host.objects.filter(id__in=ids).values_list(
                        "id", "fqdn", "provider_id"
                    )
                }
                provider_name_by_id = dict(
                    Provider.objects.filter(id__in={provider_id for _, provider_id in host_by_id.values()}).values_list(
                        "id", "name"
                    )
                )
                for target in entries:
                    fqdn, provider_id = host_by_id[target.id]
                    selectors[target] = {
                        ADCMCoreType.HOST: {"id": target.id, "name": fqdn},
                        ADCMCoreType.PROVIDER: {"id": provider_id, "name": provider_name_by_id[provider_id]},
                    }

    return selectors


def _build_selector_single(
    target: SelectorTargetDescriptor,
    owner: SelectorOwnerDescriptor | None = None,
) -> Selector:
    match target.type:
        case ADCMCoreType.ADCM:
            return {ADCMCoreType.ADCM: {"id": target.id, "name": "adcm"}}

        case ADCMHostGroupType.ACTION:
            group = ActionHostGroup.objects.select_related("object_type").get(id=target.id)
            group_owner = CoreObjectDescriptor(
                id=group.object_id, type=model_name_to_core_type(group.object_type.model)
            )
            selector = _build_selector_single(target=group_owner, owner=owner)
            selector["action_host_group"] = {"id": group.pk, "name": group.name}
            return selector

        case (
            ADCMCoreType.CLUSTER
            | ADCMCoreType.SERVICE
            | ADCMCoreType.COMPONENT
            | ADCMCoreType.PROVIDER
            | ADCMCoreType.HOST
        ):
            selector_owner = cast(SelectorOwnerDescriptor, target if owner is None else owner)

            model_ = core_type_to_model(core_type=target.type)
            query = model_.objects.values(**_SELECTOR_FIELDS_MAP[model_]).filter(id=target.id)

            match target.type, selector_owner.type:
                case (ADCMCoreType.HOST, ADCMCoreType.HOST):
                    provider_id = Host.objects.values_list("provider_id", flat=True).get(id=target.id)
                    values = Provider.objects.values(**_SELECTOR_FIELDS_MAP[Provider]).filter(id=provider_id)
                    query = query.union(values)

                case (ADCMCoreType.HOST, ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT):
                    query = query.union(_get_host_related_selector(host_id=target.id, owner=selector_owner))

                case (ADCMCoreType.SERVICE, _):
                    cluster_id = Service.objects.values_list("cluster_id", flat=True).get(id=target.id)
                    values = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
                    query = query.union(values)

                case (ADCMCoreType.COMPONENT, _):
                    cluster_id, service_id = Component.objects.values_list("cluster_id", "service_id").get(id=target.id)
                    cluster_qs = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
                    service_qs = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
                    query = query.union(cluster_qs).union(service_qs)

            return {
                entry["type_name"]: {"id": entry["object_id"], "name": entry["object_name"]} for entry in query.all()
            }


def _get_host_related_selector(host_id: HostID, owner: SelectorOwnerDescriptor) -> QuerySet:
    cluster_id = Host.objects.values_list("cluster_id", flat=True).get(id=host_id)
    if not cluster_id:
        message = "Can't detect selector for host without cluster for other targets than host itself"
        raise RuntimeError(message)

    query = Cluster.objects.values("id", object_name=F("name"), type_name=Value(ADCMCoreType.CLUSTER.value)).filter(
        id=cluster_id
    )

    if owner.type == ADCMCoreType.SERVICE:
        values = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=owner.id, cluster_id=cluster_id)
        query = query.union(values)
    elif owner.type == ADCMCoreType.COMPONENT:
        service_id, component_id = Component.objects.values_list("service_id", "id").get(
            cluster_id=cluster_id, id=owner.id
        )
        service_values = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
        component_values = Component.objects.values(**_SELECTOR_FIELDS_MAP[Component]).filter(id=component_id)
        query = query.union(service_values).union(component_values)

    return query


# States
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
