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

from datetime import timedelta
import string

ENCODING_UTF_8 = "utf-8"

API_URL = "http://localhost:8020/api/v1/"

LATIN_LETTERS_DIGITS = f"{string.ascii_letters}{string.digits}"

ALLOWED_CLUSTER_NAME_START_END_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_CLUSTER_NAME_MID_CHARS = f"{ALLOWED_CLUSTER_NAME_START_END_CHARS}-. _"

ALLOWED_HOST_FQDN_START_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_HOST_FQDN_MID_END_CHARS = f"{ALLOWED_HOST_FQDN_START_CHARS}-."

ADCM_TURN_ON_MM_ACTION_NAME = "adcm_turn_on_maintenance_mode"
ADCM_TURN_OFF_MM_ACTION_NAME = "adcm_turn_off_maintenance_mode"
ADCM_HOST_TURN_ON_MM_ACTION_NAME = "adcm_host_turn_on_maintenance_mode"
ADCM_HOST_TURN_OFF_MM_ACTION_NAME = "adcm_host_turn_off_maintenance_mode"
ADCM_DELETE_SERVICE_ACTION_NAME = "adcm_delete_service"
ADCM_SERVICE_ACTION_NAMES_SET = {
    ADCM_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_DELETE_SERVICE_ACTION_NAME,
}
ADCM_MM_ACTION_FORBIDDEN_PROPS_SET = {"config", "hc_acl", "ui_options"}
ADCM_STATUS_USERNAME = "status"
ADCM_HIDDEN_USERS = {ADCM_STATUS_USERNAME, "system"}

STACK_COMPLEX_FIELD_TYPES = {"json", "structure", "list", "map", "secretmap"}
STACK_FILE_FIELD_TYPES = {"file", "secretfile"}
STACK_NUMERIC_FIELD_TYPES = {"integer", "float"}
SECURE_PARAM_TYPES = {"password", "secrettext"}

EMPTY_REQUEST_STATUS_CODE = 32
VALUE_ERROR_STATUS_CODE = 8
EMPTY_STATUS_STATUS_CODE = 4
STATUS_REQUEST_TIMEOUT = 0.1

USERNAME_MAX_LENGTH = 150

STDOUT_STDERR_LOG_CUT_LENGTH = 1500
STDOUT_STDERR_LOG_LINE_CUT_LENGTH = 1000
STDOUT_STDERR_LOG_MAX_UNCUT_LENGTH = STDOUT_STDERR_LOG_CUT_LENGTH * STDOUT_STDERR_LOG_LINE_CUT_LENGTH
STDOUT_STDERR_TRUNCATED_LOG_MESSAGE = "<Truncated. Download full version via link>"

ACTION_PROCESS_STALE_STATE_TIMEOUT = timedelta(days=2)
