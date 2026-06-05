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

# load common functions and variables

. /etc/adcmenv

# convenient aliases

coderoot="${adcmroot}/python"
scripts="${coderoot}/application/scripts"
django_command="${coderoot}/manage.py"

#  check & prepare environment

cleanupwaitstatus
ensure_mandatory_db_settings_provided
ensure_directory_structure

"${scripts}"/manage_secrets.py migrate || exit $?

if [ -z "$MIGRATION_MODE" ] || [ "$MIGRATION_MODE" -ne 1 ]; then
    "${scripts}"/manage_secrets.py init || exit $?
fi

"${django_command}" compatibility_check || exit $?

# initialize services

sv_stop() {
    for s in nginx wsgi status; do
        /usr/sbin/sv stop /etc/sv/$s
    done
}

trap "sv_stop; exit" TERM
trap "" CHLD

runsvdir -P /etc/sv &
while (true); do wait; done;
