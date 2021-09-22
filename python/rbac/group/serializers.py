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

from django.contrib.auth.models import Group
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers


class GroupSerializer(FlexFieldsSerializerMixin, serializers.HyperlinkedModelSerializer):
    """Group serializer"""

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'url',
        )
        extra_kwargs = {
            'url': {'view_name': 'rbac_group:group-detail', 'lookup_field': 'id'},
        }
