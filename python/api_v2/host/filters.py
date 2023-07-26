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

from cm.models import Host
from django_filters.rest_framework import CharFilter, FilterSet

from adcm.filters import BaseOrderingFilter


class HostFilter(FilterSet):
    name = CharFilter(label="Host name", field_name="fqdn", lookup_expr="icontains")
    hostprovider_name = CharFilter(label="Hostprovider name", field_name="provider__name")
    cluster_name = CharFilter(label="Cluster name", field_name="cluster__name")

    class Meta:
        model = Host
        fields = ["name", "hostprovider_name", "cluster_name"]


class HostOrderingFilter(BaseOrderingFilter):
    allowed_sort_column_names = {"id", "name"}
    column_names_map = {"name": "fqdn"}
