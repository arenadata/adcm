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

. /etc/adcmenv
cleanupwaitstatus

mandatory_vars="DB_HOST DB_USER DB_PASS DB_NAME"
missing_vars=""

# Collect all missing variables
for var in $mandatory_vars; do
  eval "value=\"\${$var}\""
  if [ -z "$value" ]; then
    missing_vars="$missing_vars $var"
  fi
done

# Report and exit if any missing
if [ -n "$missing_vars" ]; then
  echo "ERROR: The following environment variables must be specified:" >&2
  for var in $missing_vars; do
    echo "  $var" >&2
  done
  exit 1
fi

sv_stop() {
    for s in nginx wsgi status; do
        /sbin/sv stop $s
    done
}

trap "sv_stop; exit" TERM
trap "" CHLD
runsvdir -P /etc/sv &
while (true); do wait; done;
