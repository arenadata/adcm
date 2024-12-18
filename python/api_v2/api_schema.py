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

from typing import Iterable, TypeAlias

from adcm.serializers import EmptySerializer
from drf_spectacular.utils import OpenApiParameter
from rest_framework.fields import CharField
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_200_OK,
)


class ErrorSerializer(EmptySerializer):
    code = CharField()
    level = CharField()
    desc = CharField()


class DefaultParams:
    LIMIT = OpenApiParameter(name="limit", description="Number of records included in the selection.", type=int)
    OFFSET = OpenApiParameter(name="offset", description="Record number from which the selection starts.", type=int)


ResponseOKType: TypeAlias = Serializer | type[Serializer] | type[dict] | type[list] | None


def responses(
    success: ResponseOKType | tuple[int, ResponseOKType], errors: Iterable[int] | int
) -> dict[int, Serializer]:
    if not isinstance(success, tuple):
        success = (HTTP_200_OK, success)

    if isinstance(errors, int):
        errors = (errors,)

    return {success[0]: success[1]} | {status: ErrorSerializer for status in errors}
