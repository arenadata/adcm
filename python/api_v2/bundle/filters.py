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
from django_filters.rest_framework import CharFilter, FilterSet

from adcm.filters import BaseOrderingFilter


class BundleFilter(FilterSet):
    display_name = CharFilter(label="Display name", field_name="prototype__display_name", lookup_expr="icontains")
    product = CharFilter(label="Product name", field_name="name", lookup_expr="iexact")

    class Meta:
        model = Bundle
        fields = ["display_name", "product"]


class BundleOrderingFilter(BaseOrderingFilter):
    pass
