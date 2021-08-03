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

name_rev=$(git name-rev --name-only HEAD)

# posible outputs
## local cloned
# feature/ADH-1376/ADH-1377 #  branches
# tags/0.1.4 #  tags
## jenkins cloned
# remotes/origin/feature/ADH-1376/ADH-1378 #   branches
# origin/pr/231/head #  pull requests
# tags/0.1.4 #  tags


case "$name_rev" in
  tags/* )
    ;;
  "master" | "remotes/origin/master" )
    ;;
  remotes/* )
    current_branch="_$(echo "$name_rev" | cut -f 3- -d '/')"
    ;;
  origin/pr/* )
    # we dont build adcm pr, only branches, just in case
    current_branch="_$(echo "$name_rev" | cut -f 2,3 -d '/' | tr '/' '-')"
    ;;
  *)
    current_branch="_$name_rev"
    ;;
esac

printf '{\n\t"version": "%s",\n\t"commit_id": "%s"\n}\n' "${current_date}" "${current_hash}${current_branch}" > config.json

# Copy information for Angular to work on
cp config.json web/src/assets/config.json
