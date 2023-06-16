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
from cm.models import HostProvider
from django_filters.rest_framework import CharFilter, FilterSet


class HostProviderFilter(FilterSet):
    hostprovider_name = CharFilter(field_name="name", label="Hostprovider name")
    type = CharFilter(field_name="prototype__type", label="Hostprovider type")
    state = CharFilter(field_name="state", label="Hostprovider state")

    class Meta:
        model = HostProvider
        fields = [
            "hostprovider_name",
            "state",
            "type",
        ]
