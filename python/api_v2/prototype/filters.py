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

from cm.models import Bundle, ObjectType, Prototype
from core.bundle import ContractVersionStatus
from django.db.models import QuerySet, Subquery
from django_filters import OrderingFilter
from django_filters.rest_framework import CharFilter, ChoiceFilter, NumberFilter
from rest_framework.request import Request

from api_v2.filters import AdvancedFilterSet
from api_v2.views import annotate_contract_version_status

_CONTRACT_VERSION_STATUS = tuple((status.value, status.value) for status in ContractVersionStatus)


def filter_contract_version_status(queryset: QuerySet, request: Request, value: str) -> QuerySet:
    bundles = Bundle.objects.annotate(
        **annotate_contract_version_status(
            contract_version_field="contract_version",
            request=request,
        )
    ).filter(contract_version_status=value)
    bundle_ids = Subquery(bundles.values("pk"))
    return queryset.filter(bundle_id__in=bundle_ids)


class ContractVersionOrderingFilter(OrderingFilter):
    def filter(self, queryset: QuerySet, value: list[str] | None) -> QuerySet:
        if value:
            queryset = queryset.annotate(
                **annotate_contract_version_status(
                    contract_version_field="bundle__contract_version",
                    request=self.parent.request,
                )
            )

        return super().filter(queryset, value)


class PrototypeFilter(
    AdvancedFilterSet,
    char_fields=("type",),
    number_fields=("id", ("bundle", "bundle__id")),
):
    bundle_id = NumberFilter(field_name="bundle__id", label="Bundle ID")
    type = ChoiceFilter(choices=ObjectType.choices, label="Type")
    display_name = CharFilter(label="Display name", field_name="display_name", lookup_expr="exact")

    contract_version_status = ChoiceFilter(
        field_name="contract_version_status",
        label="Filter by prototype bundle contract version status.",
        choices=_CONTRACT_VERSION_STATUS,
        method="filter_contract_version_status",
    )
    contract_version_value = CharFilter(
        label="Filter by prototype bundle contract version value.",
        field_name="bundle__contract_version",
        lookup_expr="exact",
    )

    ordering = ContractVersionOrderingFilter(
        fields={
            "contract_version_status": "contractVersionStatus",
            "bundle__contract_version": "contractVersionValue",
        },
        field_labels={
            "contract_version_status": "Contract version status",
            "bundle__contract_version": "Contract version value",
        },
        label="ordering",
    )

    class Meta:
        model = Prototype
        fields = ["id"]

    def filter_contract_version_status(self, queryset: QuerySet, __: str, value: str):
        return filter_contract_version_status(queryset, self.request, value)


class PrototypeVersionFilter(
    AdvancedFilterSet,
    char_fields=("type",),
):
    type = ChoiceFilter(choices=(("cluster", "cluster"), ("provider", "provider")), label="Type")

    contract_version_status = ChoiceFilter(
        field_name="contract_version_status",
        label="Filter by prototype bundle contract version status.",
        choices=_CONTRACT_VERSION_STATUS,
        method="filter_contract_version_status",
    )
    contract_version_value = CharFilter(
        label="Filter by prototype bundle contract version value.",
        field_name="bundle__contract_version",
        lookup_expr="exact",
    )

    ordering = ContractVersionOrderingFilter(
        fields={
            "contract_version_status": "contractVersionStatus",
            "bundle__contract_version": "contractVersionValue",
        },
        field_labels={
            "contract_version_status": "Contract version status",
            "bundle__contract_version": "Contract version value",
        },
        label="ordering",
    )

    class Meta:
        model = Prototype
        fields = ["type"]

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        queryset = super().filter_queryset(queryset)
        return queryset.filter(type__in=(ObjectType.CLUSTER.value, ObjectType.PROVIDER.value))

    def filter_contract_version_status(self, queryset: QuerySet, __: str, value: str):
        return filter_contract_version_status(queryset, self.request, value)
