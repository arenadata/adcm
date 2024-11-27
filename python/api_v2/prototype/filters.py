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

from cm.models import LICENSE_STATE, ObjectType, Prototype
from django_filters import CharFilter, ChoiceFilter, NumberFilter
from django_filters.rest_framework import FilterSet, OrderingFilter


class PrototypeFilter(FilterSet):
    bundle_id = NumberFilter(field_name="bundle__id", label="Bundle ID")
    type = ChoiceFilter(choices=ObjectType.choices, label="Type")
    display_name = CharFilter(label="Display name", field_name="display_name", lookup_expr="icontains")

    name = CharFilter(label="Name", lookup_expr="icontains", field_name="name")
    license = ChoiceFilter(label="License state", choices=LICENSE_STATE, field_name="license")
    version = CharFilter(label="Version", lookup_expr="icontains", field_name="version")
    description = CharFilter(label="Description", lookup_expr="icontains", field_name="description")

    ordering = OrderingFilter(
        fields={
            "id": "id",
            "display_name": "displayName",
            "name": "name",
            "version": "version",
            "description": "description",
            "license": "license",
            "type": "type",
        },
        field_labels={
            "id": "ID",
            "display_name": "Display name",
            "name": "Name",
            "version": "Version",
            "description": "Description",
            "license": "License",
            "type": "Type",
        },
    )

    class Meta:
        model = Prototype
        fields = [
            "id",
            "type",
            "bundle_id",
            "display_name",
            "name",
            "version",
            "license",
            "description",
        ]


class PrototypeVersionFilter(FilterSet):
    type = ChoiceFilter(choices=(("cluster", "cluster"), ("provider", "provider")), label="Type")

    class Meta:
        model = Prototype
        fields = ["type"]
