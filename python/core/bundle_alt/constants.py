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

import re

# copied from cm.utils
NAME_REGEX = re.compile(pattern=r"[0-9a-zA-Z_\.-]+")

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
PROVIDER_ACTION_FORBIDDEN_PROPS_SET = {"scripts_template", "config_template"}
