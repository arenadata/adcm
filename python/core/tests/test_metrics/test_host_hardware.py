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

from unittest import TestCase

from core.metrics import CapacityUnit, ResourceValue, format_size_from_bytes


class TestHostHardware(TestCase):
    def test_format_size_from_bytes(self):
        cases = [
            (
                "zero_bytes_with_gib",
                0,
                CapacityUnit.GIB,
                ResourceValue(value=0, unit=CapacityUnit.GIB),
            ),
            (
                "pib_size_with_min_repr_unit_gib",
                1024**5 + 126 * 1024**5 // 1000,
                CapacityUnit.GIB,
                ResourceValue(value=1.13, unit=CapacityUnit.PIB),
            ),
            (
                "tib_size_with_min_repr_unit_gib",
                1024**4 + 10 * 1024**4 // 100,
                CapacityUnit.GIB,
                ResourceValue(value=1.1, unit=CapacityUnit.TIB),
            ),
            (
                "gib_size_with_min_repr_unit_gib",
                1024**3 + 126 * 1024**3 // 1000,
                CapacityUnit.GIB,
                ResourceValue(value=1.13, unit=CapacityUnit.GIB),
            ),
            (
                "mib_size_with_min_repr_unit_gib",
                77 * 1024**3 // 100,
                CapacityUnit.GIB,
                ResourceValue(value=0.77, unit=CapacityUnit.GIB),
            ),
            (
                "pib_size_with_min_repr_unit_gib",
                1024**5 + 126 * 1024**5 // 1000,
                CapacityUnit.GIB,
                ResourceValue(value=1.13, unit=CapacityUnit.PIB),
            ),
            (
                "tib_size_with_min_repr_unit_gib",
                1024**4 + 10 * 1024**4 // 100,
                CapacityUnit.GIB,
                ResourceValue(value=1.1, unit=CapacityUnit.TIB),
            ),
            (
                "mib_size_with_min_repr_unit_tib",
                1024**2,
                CapacityUnit.TIB,
                ResourceValue(value=0, unit=CapacityUnit.TIB),
            ),
            (
                "gib_size_with_min_repr_unit_mib",
                1024**3 + 10 * 1024**3 // 100,
                CapacityUnit.MIB,
                ResourceValue(value=1.1, unit=CapacityUnit.GIB),
            ),
            (
                "kib_size_with_min_repr_unit_mib_with_round",
                69 * 1024,
                CapacityUnit.MIB,
                ResourceValue(value=0.07, unit=CapacityUnit.MIB),
            ),
            (
                "big_pib_size_with_min_repr_unit_gib",
                99988 * 1024**5 // 100,
                CapacityUnit.GIB,
                ResourceValue(value=999.88, unit=CapacityUnit.PIB),
            ),
            (
                "zero_bytes_with_min_repr_unit_bytes",
                0,
                CapacityUnit.BYTES,
                ResourceValue(value=0, unit=CapacityUnit.BYTES),
            ),
        ]

        for case_name, size_bytes, min_repr_unit, expected in cases:
            with self.subTest(case_name):
                resource_value = format_size_from_bytes(size_bytes, min_repr_unit)
                self.assertEqual(resource_value, expected)
