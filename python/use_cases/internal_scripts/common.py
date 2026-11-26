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


def build_result_message(
    script_name: str,
    full_complete_message: str,
    with_updates: bool,
    without_updates_message: str | None = None,
) -> str:
    base_template = "The script `{script_name}` completed successfully, {completed_info}."

    if with_updates or without_updates_message is None:
        complete_info = full_complete_message
    else:
        complete_info = f"but {without_updates_message} earlier"

    return base_template.format(script_name=script_name, completed_info=complete_info)
