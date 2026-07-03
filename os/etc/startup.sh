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

IS_IN_MM=$(is_in_maintenance_mode)

cleanupwaitstatus
echo "ADCM initialization ..."

ensure_directory_structure

if [ "$IS_IN_MM" -ne 1 ]; then
  make_nginx_default_config &&
  ensure_mandatory_db_settings_provided &&
  init_or_migrate_secrets &&
  check_compatibility &&
  migrate_db &&
  post_migrate_db &&
  upgrade_roles ||
  exit $?

  sv_stop() {
    for s in nginx wsgi status; do
        /usr/sbin/sv stop /etc/sv/$s
    done
  }

  trap "sv_stop; exit" TERM
  trap "" CHLD

  runsvdir -P /etc/sv &

  echo "ADCM launched."
  wait_forever

else
  ensure_mandatory_db_settings_provided &&
  migrate_secrets ||
  exit $?

  echo "ADCM [MAINTENANCE_MODE] launched."
  wait_forever

fi
