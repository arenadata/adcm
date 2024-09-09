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


from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import responses
from api_v2.generic.action.serializers import ActionRunSerializer
from api_v2.generic.upgrade.serializers import UpgradeListSerializer, UpgradeRetrieveSerializer


def document_upgrade_viewset(object_type: str):
    capitalized_type = object_type.capitalize()

    return extend_schema_view(
        run=extend_schema(
            operation_id=f"post{capitalized_type}Upgrade",
            summary=f"POST {object_type}'s upgrade",
            description=f"Run {object_type}'s upgrade.",
            responses={HTTP_204_NO_CONTENT: None}
            | responses(
                success=ActionRunSerializer,
                errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
            ),
        ),
        list=extend_schema(
            operation_id=f"get{capitalized_type}Upgrades",
            summary=f"GET {object_type} upgrades",
            description=f"Get a list of all {object_type}'s upgrades.",
            responses=responses(success=UpgradeListSerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}Upgrade",
            summary=f"GET {object_type} upgrade",
            description=f"Get information about a specific {object_type}'s upgrade.",
            responses=responses(success=UpgradeRetrieveSerializer, errors=HTTP_404_NOT_FOUND),
        ),
    )
