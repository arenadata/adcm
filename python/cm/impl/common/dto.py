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

"""Turning DTOs into payloads of partial DB updates"""

from typing import Any

from pydantic import BaseModel


def to_update_payload(dto: BaseModel, exclude: set[str] | None = None) -> dict[str, Any]:
    """
    Build an UPDATE payload out of the fields the caller has actually set on `dto`.

    Deliberately not `dto.model_dump(exclude_unset=True)`: that flag propagates through
    the whole object graph, so every nested model loses whatever it holds by default or
    got assigned after construction. It answers "which fields did the caller set?" for
    the DTO, which is the question worth asking, and then for its payload, which is not.

    `include` asks it of the DTO only, leaving each value to be serialized whole.

    `exclude` names fields the caller stores in a format of its own, e.g. one carrying
    a version alongside the value. They are left out of the payload entirely rather than
    dumped here and overwritten afterwards, so nothing is serialized twice.
    """

    return dto.model_dump(include=dto.model_fields_set - (exclude or set()))
