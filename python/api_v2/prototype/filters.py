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

from cm.models import ObjectType, Prototype
from django_filters import CharFilter, ChoiceFilter, NumberFilter
from django_filters.rest_framework import FilterSet


class PrototypeFilter(FilterSet):
    bundle_id = NumberFilter(field_name="bundle__id", label="Bundle ID")
    type = ChoiceFilter(choices=ObjectType.choices, label="Type")
    display_name = CharFilter(label="Display name")

    class Meta:
        model = Prototype
        fields = ["id", "type", "bundle_id"]
