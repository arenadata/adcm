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
import os

VARIABLES = [
    ("2.2", "3.0", 'max', 'min', "2.5"),
    ("2.2", "3.0", 'max', 'min_strict', "3.0"),
    ("2.2", "3.0", 'max_strict', 'min_strict', "2.5"),
    ("2.2", "3.0", 'max_strict', 'min', "2.2"),
]

TEMPLATE_EXPORT_CLUSTER = """
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
-
    type: cluster
    name: ADH
    version: {}
    config:
      required:
        type: integer
        required: true
        default: 15
      str-key:
        default: value
        type: string
        required: false

      int_key:
        type: integer
        required: false
        default: 150

    export:
      - required
      - str-key
      - int_key

- type: service
  name: hadoop
  version: 2.1

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3

  export:
      - core-site
      - quorum
"""

TEMPLATE_EXPORT_SERVICE = """
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
-
    type: cluster
    name: ADH
    version: 1.4
    config:
      required:
        type: integer
        required: true
        default: 15
      str-key:
        default: value
        type: string
        required: false

      int_key:
        type: integer
        required: false
        default: 150

    export:
      - required
      - str-key
      - int_key

- type: service
  name: hadoop
  version: {}

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3

  export:
      - core-site
      - quorum
"""

TEMPLATE_SERVICE = """
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
-
    type: cluster
    name: ADH
    version: 1.6
    import:
       hadoop:
          versions:
             {2}: {1}
             {3}: {0}
       ADH:
          versions:
             min_strict: 0.1
             max_strict: 4.0

- type: service
  name: hadoop
  version: 1.5

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3
"""

TEMPLATE_CLUSTER = """
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
-
    type: cluster
    name: ADH
    version: 1.4
    import:
       hadoop:
          versions:
             min_strict: 1.5
             max_strict: 2.5
       ADH:
          versions:
             {2}: {1}
             {3}: {0}

- type: service
  name: hadoop
  version: 2.2

  config:
     core-site:
        param1:
           type: string
           required: false
        param2:
           type: integer
           required: false
     quorum:
        type: integer
        default: 3
"""

for variable in VARIABLES:
    d_name = f"service_import/{variable[2]}_{variable[3]}"
    export_dir = d_name + "/export"
    import_dir = d_name + "/import"
    for d in d_name, export_dir, import_dir:
        os.makedirs(d)
    with open(f"{d_name}/import/config.yaml", "w+", encoding='utf_8') as f:
        f.write(TEMPLATE_SERVICE.format(variable[0], variable[1], variable[2], variable[3]))
    with open(f"{d_name}/export/config.yaml", "w+", encoding='utf_8') as f:
        f.write(TEMPLATE_EXPORT_SERVICE.format(variable[4]))

for variable in VARIABLES:
    d_name = f"cluster_import/{variable[2]}_{variable[3]}"
    export_dir = d_name + "/export"
    import_dir = d_name + "/import"
    for d in d_name, export_dir, import_dir:
        os.makedirs(d)
    with open(f"{d_name}/import/config.yaml", "w+", encoding='utf_8') as f:
        f.write(TEMPLATE_CLUSTER.format(variable[0], variable[1], variable[2], variable[3]))
    with open(f"{d_name}/export/config.yaml", "w+", encoding='utf_8') as f:
        f.write(TEMPLATE_EXPORT_CLUSTER.format(variable[4]))
