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


def generate_scripts(context: dict):
    cluster_data = context["cluster"]

    script1 = {
        "display_name": "Sleep",
        "extra_field": "extra_field",
        "name": "sleep",
        "params": {"test_params": [cluster_data["state"]]},
        "script": "no_exist_file.yaml",
        "script_type": "no_exist_type",
    }

    return [script1]
