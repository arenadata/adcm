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

import rest_framework.status as rfs
from rest_framework.exceptions import APIException

from cm.logger import log

WARN = 'warning'
ERR = 'error'
CRIT = 'critical'

ERRORS = {
    'AUTH_ERROR': ("authenticate error", rfs.HTTP_409_CONFLICT, ERR),
    'STACK_LOAD_ERROR': ("stack loading error", rfs.HTTP_409_CONFLICT, ERR),

    'ADCM_NOT_FOUND': ("adcm object doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'BUNDLE_NOT_FOUND': ("bundle doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'CLUSTER_NOT_FOUND': ("cluster doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'SERVICE_NOT_FOUND': ("service doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'BIND_NOT_FOUND': ("bind doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'PROVIDER_NOT_FOUND': ("provider doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'HOST_NOT_FOUND': ("host doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'HOST_TYPE_NOT_FOUND': ("host type doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'PROTOTYPE_NOT_FOUND': ("prototype doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'HOSTSERVICE_NOT_FOUND': (
        "map host <-> component doesn't exist",
        rfs.HTTP_404_NOT_FOUND, ERR
    ),
    'COMPONENT_NOT_FOUND': ("component doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'ACTION_NOT_FOUND': ("action for service doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'CLUSTER_SERVICE_NOT_FOUND': (
        "service is not installed in specified cluster",
        rfs.HTTP_404_NOT_FOUND, ERR
    ),
    'TASK_NOT_FOUND': ("task doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'JOB_NOT_FOUND': ("job doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'LOG_NOT_FOUND': ("log file is not found", rfs.HTTP_404_NOT_FOUND, ERR),
    'UPGRADE_NOT_FOUND': ("upgrade is not found", rfs.HTTP_404_NOT_FOUND, ERR),
    'USER_NOT_FOUND': ("user profile is not found", rfs.HTTP_404_NOT_FOUND, ERR),
    'GROUP_NOT_FOUND': ("group is not found", rfs.HTTP_404_NOT_FOUND, ERR),
    'ROLE_NOT_FOUND': ("role is not found", rfs.HTTP_404_NOT_FOUND, ERR),
    'PERMISSION_NOT_FOUND': ("permission is not found", rfs.HTTP_404_NOT_FOUND, ERR),

    'MODULE_NOT_FOUND': ("module doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'FUNCTION_NOT_FOUND': ("function doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'TASK_GENERATOR_ERROR': ("task generator error", rfs.HTTP_409_CONFLICT, ERR),

    'OBJ_TYPE_ERROR': ("wrong object type", rfs.HTTP_409_CONFLICT, ERR),

    'SERVICE_CONFLICT': ("service already exists in specified cluster", rfs.HTTP_409_CONFLICT, ERR),
    'CLUSTER_CONFLICT': ("duplicate cluster", rfs.HTTP_409_CONFLICT, ERR),
    'PROVIDER_CONFLICT': ("duplicate host provider", rfs.HTTP_409_CONFLICT, ERR),
    'HOST_CONFLICT': ("duplicate host in cluster", rfs.HTTP_409_CONFLICT, ERR),
    'USER_CONFLICT': ("duplicate user profile", rfs.HTTP_409_CONFLICT, ERR),
    'GROUP_CONFLICT': ("duplicate user group", rfs.HTTP_409_CONFLICT, ERR),
    'FOREIGN_HOST': ("host is not belong to the cluster", rfs.HTTP_409_CONFLICT, ERR),
    'COMPONENT_CONFLICT': ("duplicate component on host in cluster", rfs.HTTP_409_CONFLICT, ERR),
    'COMPONENT_CONSTRAINT_ERROR': ("component constraint error", rfs.HTTP_409_CONFLICT, ERR),
    'BUNDLE_CONFIG_ERROR': ("bundle config error", rfs.HTTP_409_CONFLICT, ERR),
    'BUNDLE_CONFLICT': ("bundle conflict error", rfs.HTTP_409_CONFLICT, ERR),
    'ROLE_ERROR': ("role error", rfs.HTTP_409_CONFLICT, ERR),

    'INVALID_OBJECT_DEFINITION': ("invalid object definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_CONFIG_DEFINITION': ("invalid config definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_COMPONENT_DEFINITION': ("invalid component definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_ACTION_DEFINITION': ("invalid action definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_UPGRADE_DEFINITION': ("invalid upgrade definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_VERSION_DEFINITION': ("invalid version definition", rfs.HTTP_409_CONFLICT, ERR),

    'INVALID_OBJECT_UPDATE': ("invalid update of object definition", rfs.HTTP_409_CONFLICT, ERR),
    'INVALID_CONFIG_UPDATE': ("invalid update of config definition", rfs.HTTP_409_CONFLICT, ERR),

    'BUNDLE_ERROR': ("bundle error", rfs.HTTP_409_CONFLICT, ERR),
    'BUNDLE_VERSION_ERROR': ("bundle version error", rfs.HTTP_409_CONFLICT, ERR),
    'BUNDLE_UPLOAD_ERROR': ("bundle upload error", rfs.HTTP_409_CONFLICT, ERR),

    'LICENSE_ERROR': ("license error", rfs.HTTP_409_CONFLICT, ERR),

    'BIND_ERROR': ("bind error", rfs.HTTP_409_CONFLICT, ERR),

    'CONFIG_NOT_FOUND': ("config param doesn't exist", rfs.HTTP_404_NOT_FOUND, ERR),
    'SERVICE_CONFIG_ERROR': ("service config parsing error", rfs.HTTP_409_CONFLICT, ERR),
    'CONFIG_TYPE_ERROR': ("config type error", rfs.HTTP_409_CONFLICT, ERR),
    'DEFINITION_KEY_ERROR': ("config key error", rfs.HTTP_409_CONFLICT, ERR),
    'DEFINITION_TYPE_ERROR': ("config type error", rfs.HTTP_409_CONFLICT, ERR),

    'UPGRADE_ERROR': ("upgrade error", rfs.HTTP_409_CONFLICT, ERR),

    'ACTION_ERROR': ("action error", rfs.HTTP_409_CONFLICT, ERR),
    'TASK_ERROR': ("task error", rfs.HTTP_409_CONFLICT, ERR),
    'TASK_IS_FAILED': ("task is failed", rfs.HTTP_409_CONFLICT, ERR),
    'TASK_IS_ABORTED': ("task is aborted", rfs.HTTP_409_CONFLICT, ERR),
    'TASK_IS_SUCCESS': ("task is success", rfs.HTTP_409_CONFLICT, ERR),
    'NOT_ALLOWED_TERMINATION': ("not allowed termination the task", rfs.HTTP_409_CONFLICT, ERR),
    'WRONG_SELECTOR': ("selector error", rfs.HTTP_409_CONFLICT, ERR),

    'WRONG_JOB_TYPE': ("unknown job type", rfs.HTTP_409_CONFLICT, ERR),
    'WRONG_ACTION_CONTEXT': ("unknown action context", rfs.HTTP_409_CONFLICT, ERR),
    'WRONG_ACTION_TYPE': ("config action type error", rfs.HTTP_409_CONFLICT, ERR),
    'WRONG_ACTION_HC': ("action hostcomponentmap error", rfs.HTTP_409_CONFLICT, ERR),
    'WRONG_CLUSTER_ID_TYPE': ("cluster id must be integer", rfs.HTTP_400_BAD_REQUEST, ERR),
    'WRONG_NAME': ("wrong name", rfs.HTTP_400_BAD_REQUEST, ERR),
    'LONG_NAME': ("name is too long", rfs.HTTP_400_BAD_REQUEST, ERR),

    'INVALID_INPUT': ("invalid input", rfs.HTTP_400_BAD_REQUEST, ERR),

    'JSON_ERROR': ("json decoding error", rfs.HTTP_400_BAD_REQUEST, ERR),
    'CONFIG_KEY_ERROR': ("error in json config", rfs.HTTP_400_BAD_REQUEST, ERR),
    'CONFIG_VALUE_ERROR': ("error in json config", rfs.HTTP_400_BAD_REQUEST, ERR),
    'ATTRIBUTE_ERROR': ("error in attribute config", rfs.HTTP_400_BAD_REQUEST, ERR),

    'TOO_LONG': ("response is too long", rfs.HTTP_400_BAD_REQUEST, WARN),
    'NOT_IMPLEMENTED': ("not implemented yet", rfs.HTTP_501_NOT_IMPLEMENTED, ERR),
    'NO_JOBS_RUNNING': ("no jobs running", rfs.HTTP_409_CONFLICT, ERR),
    'BAD_QUERY_PARAMS': ("bad query params", rfs.HTTP_400_BAD_REQUEST),
    'JSON_DB_ERROR': ("Not correct field format", rfs.HTTP_409_CONFLICT, ERR),
}


def get_error(code):
    if code in ERRORS:
        err = ERRORS[code]
        if len(err) == 1:
            return (code, err[0], rfs.HTTP_404_NOT_FOUND, ERR)
        elif len(err) == 2:
            return (code, err[0], err[1], ERR)
        else:
            return (code, err[0], err[1], err[2])
    else:
        msg = 'unknow error: "{}"'.format(code)
        return ('UNKNOWN_ERROR', msg, rfs.HTTP_501_NOT_IMPLEMENTED, CRIT)


class AdcmEx(Exception):
    def __init__(self, code, msg='', http_code='', args=''):
        (err_code, err_msg, err_http_code, level) = get_error(code)
        if msg != '':
            err_msg = msg
        if http_code != '':
            err_http_code = http_code
        self.msg = err_msg
        self.code = err_code
        self.http_code = err_http_code
        self.level = level
        self.adds = args
        super().__init__(err_msg)

    def __str__(self):
        return self.msg


class AdcmApiEx(APIException):
    def __init__(self, code, msg='', http_code='', args=''):
        (err_code, err_msg, err_http_code, level) = get_error(code)
        if msg != '':
            err_msg = msg
        if http_code != '':
            err_http_code = http_code
        self.status_code = err_http_code
        detail = {
            'code': err_code,
            'level': level,
            'desc': err_msg,
        }
        if err_code == 'UNKNOWN_ERROR':
            detail['args'] = code
        elif args:
            detail['args'] = args
        super().__init__(detail, err_http_code)


def raise_AdcmEx(code, msg='', args=''):
    (_, err_msg, _, _) = get_error(code)
    if msg != '':
        err_msg = msg
    log.error(err_msg)
    raise AdcmEx(code, msg=msg, args=args)
