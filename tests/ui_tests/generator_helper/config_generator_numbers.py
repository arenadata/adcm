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
"""Config generator for UI tests"""

import os

integers = [
    (0, 0, 0, "nulls"),
    (-10, 5, 0, "positive_and_negative"),
    (0, 10, 10, "positive_and_null"),
    (-10, -1, -2, "negative"),
    (1, 10, 5, "positive"),
]
floats = [
    (0.0, 0.0, 0.0, "nulls"),
    (-10.5, 0.2, 0.1, "positive_and_negative"),
    (0, 10.5, 2.5, "positive_and_null"),
    (-10.3, -1.4444, -2.234, "negative"),
    (1.1, 20.2, 5.5, "positive"),
]
FLOAT_TEMPLATE = """
- type: cluster
  name: numbers_test
  version: 1
  config:
    - name: numbers_test
      type: float
      required: true
      min: {0}
      max: {1}
      default: {2}
"""
INTEGER_TEMPLATE = """
- type: cluster
  name: numbers_test
  version: 1
  config:
    - name: numbers_test
      type: integer
      required: true
      min: {0}
      max: {1}
      default: {2}
"""

for fl in floats:
    d_name = f"bundles/{f'float-{fl[3]}'}"
    os.makedirs(d_name)
    with open(f"{d_name}/config.yaml", "w+", encoding="utf_8") as f:
        f.write(FLOAT_TEMPLATE.format(fl[0], fl[1], fl[2]))

for i in integers:
    d_name = f"bundles/{f'integer-{i[3]}'}"
    os.makedirs(d_name)
    with open(f"{d_name}/config.yaml", "w+", encoding="utf_8") as f:
        f.write(INTEGER_TEMPLATE.format(i[0], i[1], i[2]))
