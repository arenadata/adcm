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
from cm.models import Bundle
from django_filters import DateFilter
from django_filters.rest_framework import CharFilter, FilterSet


class BundleFilter(FilterSet):
    name = CharFilter(field_name="name", label="Bundle name")
    version = CharFilter(field_name="version", label="Bundle version")
    edition = CharFilter(field_name="edition", label="Bundle edition")
    date = DateFilter(field_name="date", lookup_expr="date", label="Bundle upload date")
    product = CharFilter(field_name="category__value", label="Product name")

    class Meta:
        model = Bundle
        fields = [
            "name",
            "version",
            "edition",
            "date",
            "product",
        ]
