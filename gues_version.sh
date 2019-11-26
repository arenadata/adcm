#!/bin/sh
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

current_date=$(date '+%Y.%m.%d.%H')
current_hash=$(git log --pretty=format:'%h' -n 1)

printf '{\n\t"version": "%s",\n\t"commit_id": "%s"\n}\n' "${current_date}" "${current_hash}" > config.json

# Copy information for Angular to work on
cp config.json web/src/assets/config.json
