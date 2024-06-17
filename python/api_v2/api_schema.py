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

from adcm.serializers import EmptySerializer
from drf_spectacular.utils import OpenApiParameter
from rest_framework.fields import CharField
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT


class ErrorSerializer(EmptySerializer):
    code = CharField()
    level = CharField()
    desc = CharField()


DOCS_DEFAULT_ERROR_RESPONSES = {HTTP_403_FORBIDDEN: ErrorSerializer, HTTP_404_NOT_FOUND: ErrorSerializer}
DOCS_CLIENT_INPUT_ERROR_RESPONSES = {HTTP_400_BAD_REQUEST: ErrorSerializer, HTTP_409_CONFLICT: ErrorSerializer}


class DefaultParams:
    LIMIT = OpenApiParameter(name="limit", description="Number of records included in the selection.", type=int)
    OFFSET = OpenApiParameter(name="offset", description="Record number from which the selection starts.", type=int)
    ORDERING = OpenApiParameter(
        name="ordering",
        required=False,
        location=OpenApiParameter.QUERY,
        description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
        type=str,
    )

    @classmethod
    def ordering_by(cls, *values: str | tuple[str, str], **kwargs: str | bool | type) -> OpenApiParameter:
        return OpenApiParameter(
            location=OpenApiParameter.QUERY,
            enum=values,
            **{attr: getattr(cls.ORDERING, attr) for attr in ("name", "required", "description", "type")} | kwargs,
        )
