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
    ("invisible", "true", "advanced", "true"),
    ("invisible", "false", "advanced", "false"),
    ("invisible", "false", "advanced", "true"),
    ("invisible", "true", "advanced", "false"),
]
TYPES = (
    "string",
    "password",
    "integer",
    "text",
    "boolean",
    "float",
    "option",
    "list",
    "map",
    "json",
    "file",
)
TEMPLATE_TEXTBOXES = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: {4}
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_PASSWORD = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: password
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_TEXT = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: text
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_NUMBERS = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: 1
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_BOOLEAN = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      read_only: [created]
      default: true
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_FILE = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_JSON = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      default: {{}}
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""
TEMPLATE_MAP = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      read_only: [created]
      default:
        name: Joe
        age: "24"
        sex: m
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_LIST = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      read_only: [created]
      default:
        - /dev/rdisk0s1
        - /dev/rdisk0s2
        - /dev/rdisk0s3
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""

TEMPLATE_OPTION = """
- type: cluster
  name: {0}_{1}_{2}_{3}_{4}
  version: 1
  config:
    - name: {4}
      type: {4}
      option: {{http: 80, https: 443}}
      default: 80
      read_only: [created]
      ui_options:
         {0}: {1}
         {2}: {3}
  actions:
    install:
      type: job
      script_type: ansible
      script: ansible/install.yaml
      params:
        ansible_tags: install

      states:
        available:
          - created
        on_success: installed
        on_fail: created
"""
TEMPLATES = {
    "string": TEMPLATE_TEXTBOXES,
    "password": TEMPLATE_PASSWORD,
    "integer": TEMPLATE_NUMBERS,
    "text": TEMPLATE_TEXT,
    "boolean": TEMPLATE_BOOLEAN,
    "float": TEMPLATE_NUMBERS,
    "option": TEMPLATE_OPTION,
    "list": TEMPLATE_LIST,
    "map": TEMPLATE_MAP,
    "json": TEMPLATE_JSON,
    "file": TEMPLATE_FILE,
}
INSTALL = """
---
- name: Do nothing playbook
  hosts: all
  connection: local
  gather_facts: no

  tasks:
    - name: emulation install all item of the cluster
      pause:
        seconds: 5
    - debug:
        msg: "Unstucked now"
"""


for t in TYPES:
    for config in DATA:
        d_name = f"{config[0]}_{config[1]}_{config[2]}_{config[3]}/{t}"
        os.makedirs(d_name)
        os.makedirs(f"{config[0]}_{config[1]}_{config[2]}_{config[3]}/{t}/ansible")
        TMPL = ""
        with open(f"{d_name}/config.yaml", "w+", encoding="utf_8") as f:
            f.write(TEMPLATES[t].format(config[0], config[1], config[2], config[3], t))
        with open(f"{d_name}/ansible/install.yaml", "w+", encoding="utf_8") as f:
            f.write(INSTALL)