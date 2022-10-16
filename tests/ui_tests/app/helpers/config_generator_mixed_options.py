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

DATA = [
    (g_i, g_a, f_g, f_i)
    for g_i in ['true', 'false']
    for g_a in ['true', 'false']
    for f_g in ['true', 'false']
    for f_i in ['true', 'false']
]
TYPES = (
    "string",
    "password",
    "integer",
    "text",
    'boolean',
    'float',
    'option',
    'list',
    'map',
    'json',
    'file',
)
TEMPLATE_STRING = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        default: {4}
        display_name: {4}
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_NUMBERS = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        default: 1
        display_name: {4}
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_BOOLEAN = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        default: true
        display_name: {4}
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_FILE = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_JSON = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        default: {{}}
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_LIST = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        default:
        - /dev/rdisk0s1
        - /dev/rdisk0s2
        - /dev/rdisk0s3
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_MAP = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        default:
          name: Joe
          age: "24"
          sex: m
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_OPTION = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        option: {{http: 80, https: 443}}
        default: 80
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_PASSWORD = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        default: password
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATE_TEXT = """
- type: cluster
  name: group_advanced_{0}_invisible_{1}_field_advanced_{2}_invisible_{3}
  version: 1
  config:
    - description: {4}
      display_name: {4}
      name: group
      type: group
      ui_options:
        advanced: {0}
        invisible: {1}
      subs: &id001
      - &id002
        name: {4}
        display_name: {4}
        default: text
        type: {4}
        ui_options:
         advanced: {2}
         invisible: {3}
"""

TEMPLATES = {
    "string": TEMPLATE_STRING,
    "password": TEMPLATE_PASSWORD,
    "integer": TEMPLATE_NUMBERS,
    "text": TEMPLATE_TEXT,
    'boolean': TEMPLATE_BOOLEAN,
    'float': TEMPLATE_NUMBERS,
    'option': TEMPLATE_OPTION,
    'list': TEMPLATE_LIST,
    'map': TEMPLATE_MAP,
    'json': TEMPLATE_JSON,
    'file': TEMPLATE_FILE,
}


for t in TYPES:
    for config in DATA:
        d_name = (
            f"group_advanced_{config[0]}_invisible_{config[1]}_field_advanced_{config[2]}_invisible_{config[3]}/{t}"
        )
        os.makedirs(d_name)
        tmpl = ''
        with open(f"{d_name}/config.yaml", "w+", encoding='utf_8') as f:
            f.write(TEMPLATES[t].format(config[0], config[1], config[2], config[3], t))
