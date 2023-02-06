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

SERVICE_VERSIONS = (
    ("service-less-equal", "2.2", "3.0"),
    ("service-greater-equal", "1.5", "2.2"),
    ("service-equal", "2.2", "2.2"),
    ("service-less", "2.3", "2.4"),
    ("service-greater", "1", "2"),
)

CLUSTER_VERSIONS = (
    ("cluster-less-equal", "1.6", "2.0"),
    ("cluster-greater-equal", "1.0", "1.6"),
    ("cluster-equal", "1.6", "1.6"),
    ("cluster-less", "1.7", "2.4"),
    ("cluster-greater", "0.5", "0.9"),
)
TEMPLATE_SERVICE = """
-
    type: cluster
    name: ADH
    version: 1.6
    upgrade:
      - versions:
          min: 0.4
          max: 1.5
        name: upgrade to 1.6
        description: New cool upgrade
        states:
          available: any
          on_success: upgradable
      - versions:
          min: 1.0
          max: 1.8
        description: Super new upgrade
        name: upgrade 2
        states:
          available: [created, installed, upgradable]
          on_success: upgradated
    import:
       hadoop:
          versions:
             min_strict: {0}
             max_strict: {1}
       ADH:
          versions:
             min_strict: 0.1
             max_strict: 4.0

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

TEMPLATE_CLUSTER = """
-
    type: cluster
    name: ADH
    version: 1.6
    upgrade:
      - versions:
          min: 0.4
          max: 1.5
        name: upgrade to 1.6
        description: New cool upgrade
        states:
          available: any
          on_success: upgradable
      - versions:
          min: 1.0
          max: 1.8
        description: Super new upgrade
        name: upgrade 2
        states:
          available: [created, installed, upgradable]
          on_success: upgradated
    import:
       hadoop:
          versions:
             min_strict: 1.5
             max_strict: 2.5
       ADH:
          versions:
             min_strict: {0}
             max_strict: {1}

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

for t in SERVICE_VERSIONS:
    d_name = f"upgradable_cluster_with_strict_incorrect_version/{t[0]}"
    os.makedirs(d_name)
    with open(f"{d_name}/config.yaml", "w+", encoding="utf_8") as f:
        f.write(TEMPLATE_SERVICE.format(t[1], t[2]))

for t in CLUSTER_VERSIONS:
    d_name = f"upgradable_cluster_with_strict_incorrect_version/{t[0]}"
    os.makedirs(d_name)
    with open(f"{d_name}/config.yaml", "w+", encoding="utf_8") as f:
        f.write(TEMPLATE_CLUSTER.format(t[1], t[2]))
