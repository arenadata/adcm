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

from cm.models import LICENSE_STATE, Bundle, ObjectType, SignatureStatus
from django.db.models.query import QuerySet
from django_filters.rest_framework import CharFilter, ChoiceFilter, NumberFilter, OrderingFilter

from api_v2.filters import AdvancedFilterSet, CharInFilter


class BundleFilter(
    AdvancedFilterSet,
    char_fields=("name", "version", "edition"),
    number_fields=("id",),
):
    # Advanced filters
    display_name__eq = CharFilter(
        field_name="prototype__display_name__exact",
        label="display_name__eq",
        method="advanced_filter_by_display_name",
    )
    display_name__ieq = CharFilter(
        field_name="prototype__display_name__iexact",
        label="display_name__ieq",
        method="advanced_filter_by_display_name",
    )
    display_name__ne = CharFilter(
        field_name="prototype__display_name__ne",
        label="display_name__ne",
        method="advanced_filter_by_display_name",
    )
    display_name__ine = CharFilter(
        field_name="prototype__display_name__ine",
        label="display_name__ine",
        method="advanced_filter_by_display_name",
    )
    display_name__contains = CharFilter(
        field_name="prototype__display_name__contains",
        label="display_name__contains",
        method="advanced_filter_by_display_name",
    )
    display_name__icontains = CharFilter(
        field_name="prototype__display_name__icontains",
        label="display_name__icontains",
        method="advanced_filter_by_display_name",
    )
    display_name__in = CharInFilter(
        field_name="prototype__display_name__in",
        label="display_name__in",
        method="advanced_filter_by_display_name",
    )
    display_name__iin = CharInFilter(
        field_name="prototype__display_name__lower__in",
        label="display_name__iin",
        method="advanced_filter_by_display_name",
    )
    display_name__exclude = CharInFilter(
        field_name="prototype__display_name__in",
        label="display_name__exclude",
        method="advanced_filter_by_display_name_exclude",
    )
    display_name__iexclude = CharInFilter(
        field_name="prototype__display_name__lower__in",
        label="display_name__iexclude",
        method="advanced_filter_by_display_name_exclude",
    )
    # ---
    id = NumberFilter(field_name="id", label="Filter by id.")
    display_name = CharFilter(
        label="Case insensitive and partial filter by display name.",
        field_name="display_name",
        lookup_expr="icontains",
    )
    product = CharFilter(
        label="Case insensitive filter by product.", field_name="prototype__name", lookup_expr="iexact"
    )
    version = CharFilter(label="Filter by version.", field_name="version", lookup_expr="exact")
    edition = CharFilter(label="Filter by edition.", field_name="edition", lookup_expr="exact")
    signature_status = ChoiceFilter(
        label="Filter by bundle signature status.",
        field_name="signature_status",
        choices=SignatureStatus.choices,
    )
    main_prototype_license_status = ChoiceFilter(
        label="Filter by bundle license status.",
        field_name="main_prototype_license",
        choices=LICENSE_STATE,
    )
    ordering = OrderingFilter(
        fields={
            "display_name": "displayName",
            "date": "uploadTime",
            "version": "version",
            "edition": "edition",
            "signature_status": "signatureStatus",
            "main_prototype_license": "mainPrototypeLicenseStatus",
        },
        field_labels={
            "display_name": "Display name",
            "date": "Upload time",
            "version": "Version",
            "edition": "Edition",
            "signature_status": "Signature status",
            "main_prototype_license": "License status",
        },
        label="ordering",
    )

    def advanced_filter_by_display_name(
        self, queryset: QuerySet[Bundle], name: str, value: Collection[str] | str
    ) -> QuerySet[Bundle]:
        return queryset.filter(**{f"{name}": value, "prototype__type__in": [ObjectType.CLUSTER, ObjectType.PROVIDER]})

    def advanced_filter_by_display_name_exclude(
        self, queryset: QuerySet[Bundle], name: str, value: Collection[str] | str
    ) -> QuerySet[Bundle]:
        return queryset.exclude(**{f"{name}": value, "prototype__type__in": [ObjectType.CLUSTER, ObjectType.PROVIDER]})
