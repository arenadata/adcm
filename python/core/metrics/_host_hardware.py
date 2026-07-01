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

from collections import OrderedDict

from core.metrics._types import CapacityUnit, ResourceValue

_UNIT_TO_BYTES: OrderedDict[CapacityUnit, int] = OrderedDict(
    (
        (CapacityUnit.PIB, 1024**5),
        (CapacityUnit.TIB, 1024**4),
        (CapacityUnit.GIB, 1024**3),
        (CapacityUnit.MIB, 1024**2),
        (CapacityUnit.KIB, 1024),
        (CapacityUnit.BYTES, 1),
    )
)


def format_size_from_bytes(
    size_bytes: int,
    min_repr_unit: CapacityUnit = CapacityUnit.GIB,
) -> ResourceValue:
    unit = min_repr_unit
    divisor = _UNIT_TO_BYTES[min_repr_unit]

    for current_unit, unit_bytes in _UNIT_TO_BYTES.items():
        if size_bytes >= unit_bytes or current_unit == min_repr_unit:
            unit = current_unit
            divisor = unit_bytes
            break

    value = round(size_bytes / divisor, 2)
    return ResourceValue(value=value, unit=unit)
