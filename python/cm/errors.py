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

from django.conf import settings
from django.db.utils import OperationalError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)
from rest_framework.views import exception_handler

from cm.logger import logger

WARN = "warning"
ERR = "error"
CRIT = "critical"

ERRORS = {
    "AUTH_ERROR": ("Wrong user or password", HTTP_401_UNAUTHORIZED, ERR),
    "STACK_LOAD_ERROR": ("stack loading error", HTTP_409_CONFLICT, ERR),
    "NO_MODEL_ERROR_CODE": (
        "django model doesn't has __error_code__ attribute",
        HTTP_404_NOT_FOUND,
        ERR,
    ),
    "BUNDLE_NOT_FOUND": ("bundle doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "CLUSTER_NOT_FOUND": ("cluster doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "SERVICE_NOT_FOUND": ("service doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "BIND_NOT_FOUND": ("bind doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "PROVIDER_NOT_FOUND": ("provider doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "HOST_NOT_FOUND": ("host doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "PROTOTYPE_NOT_FOUND": ("prototype doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "HOSTSERVICE_NOT_FOUND": ("map host <-> component doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "COMPONENT_NOT_FOUND": ("component doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "ACTION_NOT_FOUND": ("action for service doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "CLUSTER_SERVICE_NOT_FOUND": (
        "service is not installed in specified cluster",
        HTTP_404_NOT_FOUND,
        ERR,
    ),
    "TASK_NOT_FOUND": ("task doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "JOB_NOT_FOUND": ("job doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "LOG_NOT_FOUND": ("log file is not found", HTTP_404_NOT_FOUND, ERR),
    "UPGRADE_NOT_FOUND": ("upgrade is not found", HTTP_404_NOT_FOUND, ERR),
    "USER_NOT_FOUND": ("user profile is not found", HTTP_404_NOT_FOUND, ERR),
    "CONCERNITEM_NOT_FOUND": ("concern item doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "CONCERNITEM_NOT_REMOVED": ("concern item can't be removed", HTTP_409_CONFLICT, ERR),
    "GROUP_CONFIG_NOT_FOUND": ("group config doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "OBJ_TYPE_ERROR": ("wrong object type", HTTP_409_CONFLICT, ERR),
    "SERVICE_CONFLICT": ("service already exists in specified cluster", HTTP_409_CONFLICT, ERR),
    "CLUSTER_CONFLICT": ("duplicate cluster", HTTP_409_CONFLICT, ERR),
    "PROVIDER_CONFLICT": ("duplicate host provider", HTTP_409_CONFLICT, ERR),
    "HOST_CONFLICT": ("duplicate host in cluster", HTTP_409_CONFLICT, ERR),
    "USER_CONFLICT": ("duplicate user profile", HTTP_409_CONFLICT, ERR),
    "GROUP_CONFLICT": ("duplicate user group", HTTP_409_CONFLICT, ERR),
    "FOREIGN_HOST": ("host is not belong to the cluster", HTTP_409_CONFLICT, ERR),
    "COMPONENT_CONSTRAINT_ERROR": ("component constraint error", HTTP_409_CONFLICT, ERR),
    "REQUIRES_ERROR": ("Incorrect requires definition", HTTP_409_CONFLICT, ERR),
    "BUNDLE_CONFLICT": ("bundle conflict error", HTTP_409_CONFLICT, ERR),
    "INVALID_ROLE_SPEC": ("role specification error", HTTP_409_CONFLICT, ERR),
    "INVALID_OBJECT_DEFINITION": ("invalid object definition", HTTP_409_CONFLICT, ERR),
    "INVALID_CONFIG_DEFINITION": ("invalid config definition", HTTP_409_CONFLICT, ERR),
    "INVALID_COMPONENT_DEFINITION": ("invalid component definition", HTTP_409_CONFLICT, ERR),
    "INVALID_ACTION_DEFINITION": ("invalid action definition", HTTP_409_CONFLICT, ERR),
    "INVALID_UPGRADE_DEFINITION": ("invalid upgrade definition", HTTP_409_CONFLICT, ERR),
    "INVALID_VERSION_DEFINITION": ("invalid version definition", HTTP_409_CONFLICT, ERR),
    "INVALID_CONFIG_UPDATE": ("invalid update of config definition", HTTP_409_CONFLICT, ERR),
    "BUNDLE_ERROR": ("bundle error", HTTP_409_CONFLICT, ERR),
    "BUNDLE_DEFINITION_ERROR": ("incorrect definition of bundle object", HTTP_409_CONFLICT, ERR),
    "BUNDLE_VALIDATION_ERROR": ("bundle definitions won't work", HTTP_409_CONFLICT, ERR),
    "BUNDLE_VERSION_ERROR": ("bundle version error", HTTP_409_CONFLICT, ERR),
    "LICENSE_ERROR": ("license error", HTTP_409_CONFLICT, ERR),
    "BIND_ERROR": ("bind error", HTTP_409_CONFLICT, ERR),
    "CONFIG_NOT_FOUND": ("config param doesn't exist", HTTP_404_NOT_FOUND, ERR),
    "CONFIG_TYPE_ERROR": ("config type error", HTTP_409_CONFLICT, ERR),
    "UPGRADE_ERROR": ("upgrade error", HTTP_409_CONFLICT, ERR),
    "ACTION_ERROR": ("action error", HTTP_409_CONFLICT, ERR),
    "TASK_ERROR": ("task error", HTTP_409_CONFLICT, ERR),
    "TASK_IS_FAILED": ("task is failed", HTTP_409_CONFLICT, ERR),
    "TASK_IS_ABORTED": ("task is aborted", HTTP_409_CONFLICT, ERR),
    "TASK_IS_SUCCESS": ("task is success", HTTP_409_CONFLICT, ERR),
    "NOT_ALLOWED_TERMINATION": ("not allowed termination the task", HTTP_409_CONFLICT, ERR),
    "WRONG_ACTION_HC": ("action hostcomponentmap error", HTTP_409_CONFLICT, ERR),
    "OVERFLOW": ("integer or floats in a request cause an overflow", HTTP_400_BAD_REQUEST, ERR),
    "WRONG_NAME": ("wrong name", HTTP_400_BAD_REQUEST, ERR),
    "INVALID_INPUT": ("invalid input", HTTP_400_BAD_REQUEST, ERR),
    "JSON_ERROR": ("json decoding error", HTTP_400_BAD_REQUEST, ERR),
    "CONFIG_KEY_ERROR": ("error in json config", HTTP_400_BAD_REQUEST, ERR),
    "CONFIG_VALUE_ERROR": ("error in json config", HTTP_400_BAD_REQUEST, ERR),
    "ATTRIBUTE_ERROR": ("error in attribute config", HTTP_400_BAD_REQUEST, ERR),
    "CONFIG_VARIANT_ERROR": ("error in config variant type", HTTP_400_BAD_REQUEST, ERR),
    "TOO_LONG": ("response is too long", HTTP_400_BAD_REQUEST, WARN),
    "NO_JOBS_RUNNING": ("no jobs running", HTTP_409_CONFLICT, ERR),
    "BAD_QUERY_PARAMS": ("bad query params", HTTP_400_BAD_REQUEST, ERR),
    "WRONG_PASSWORD": ("Incorrect password during loading", HTTP_400_BAD_REQUEST, ERR),
    "ISSUE_INTEGRITY_ERROR": ("Issue object integrity error", HTTP_409_CONFLICT, ERR),
    "GROUP_CONFIG_HOST_ERROR": (
        "host is not available for this object, or host already is a member of another group of this object",
        HTTP_409_CONFLICT,
    ),
    "GROUP_CONFIG_HOST_EXISTS": (
        "the host is already a member of this group ",
        HTTP_409_CONFLICT,
    ),
    "NOT_CHANGEABLE_FIELDS": ("fields cannot be changed", HTTP_400_BAD_REQUEST, ERR),
    "GROUP_CONFIG_TYPE_ERROR": (
        "invalid type object for group config, valid types: `cluster`, `service`, `component` and `provider`",
        HTTP_400_BAD_REQUEST,
        ERR,
    ),
    "GROUP_CONFIG_DATA_ERROR": (
        "invalid data for creating group_config",
        HTTP_400_BAD_REQUEST,
        ERR,
    ),
    "GROUP_CONFIG_NO_CONFIG_ERROR": (
        "Can't create group config for object without config",
        HTTP_409_CONFLICT,
        ERR,
    ),
    "LOCK_ERROR": ("lock error", HTTP_409_CONFLICT, ERR),
    "MAINTENANCE_MODE_NOT_AVAILABLE": (
        "you can't manage host maintenance mode",
        HTTP_409_CONFLICT,
        ERR,
    ),
    "INVALID_HC_HOST_IN_MM": (
        "You can't save hc with hosts in maintenance mode",
        HTTP_409_CONFLICT,
        ERR,
    ),
    "NO_CERT_FILE": (
        "missing cert file for `ldaps://` connection",
        HTTP_400_BAD_REQUEST,
        ERR,
    ),
    "NO_LDAP_SETTINGS": (
        "disabled ldap settings",
        HTTP_400_BAD_REQUEST,
        ERR,
    ),
    "AUDIT_OPERATIONS_FORBIDDEN": (
        "access to audit of operations is forbidden",
        HTTP_403_FORBIDDEN,
        ERR,
    ),
    "AUDIT_LOGINS_FORBIDDEN": (
        "access to audit of logins is forbidden",
        HTTP_403_FORBIDDEN,
        ERR,
    ),
    "HOST_UPDATE_ERROR": (
        "FQDN can't be changed if cluster bound or not CREATED state",
        HTTP_409_CONFLICT,
        ERR,
    ),
    "SERVICE_DELETE_ERROR": ("Service can't be deleted if it has not CREATED state", HTTP_409_CONFLICT, ERR),
    "ROLE_MODULE_ERROR": ("No role module with this name", HTTP_409_CONFLICT, ERR),
    "ROLE_CLASS_ERROR": ("No matching class in this module", HTTP_409_CONFLICT, ERR),
    "ROLE_FILTER_ERROR": ("Incorrect filter in role", HTTP_409_CONFLICT, ERR),
    "ROLE_CREATE_ERROR": ("A role with this name already exists", HTTP_409_CONFLICT, ERR),
    "ROLE_UPDATE_ERROR": ("Error during process of role updating", HTTP_409_CONFLICT, ERR),
    "ROLE_CONFLICT": (
        "Combination of cluster/service/component and provider permissions is not allowed",
        HTTP_409_CONFLICT,
        ERR,
    ),
    "ROLE_DELETE_ERROR": ("Error during process of role deleting", HTTP_409_CONFLICT, ERR),
    "GROUP_CREATE_ERROR": ("Error during process of group creating", HTTP_409_CONFLICT, ERR),
    "GROUP_UPDATE_ERROR": ("Error during process of group updating", HTTP_400_BAD_REQUEST, ERR),
    "GROUP_DELETE_ERROR": ("Built-in group could not be deleted", HTTP_409_CONFLICT, ERR),
    "POLICY_INTEGRITY_ERROR": ("Incorrect role or user list of policy", HTTP_409_CONFLICT, ERR),
    "POLICY_CREATE_ERROR": ("Error during process of policy creating", HTTP_409_CONFLICT, ERR),
    "POLICY_UPDATE_ERROR": ("Error during process of policy updating", HTTP_409_CONFLICT, ERR),
    "POLICY_DELETE_ERROR": ("Error during process of policy deleting", HTTP_409_CONFLICT, ERR),
    "USER_CREATE_ERROR": ("Error during process of user creating", HTTP_409_CONFLICT, ERR),
    "USER_UPDATE_ERROR": ("Error during process of user updating", HTTP_400_BAD_REQUEST, ERR),
    "USER_DELETE_ERROR": ("Built-in user could not be deleted", HTTP_409_CONFLICT, ERR),
    "USER_BLOCK_ERROR": ("Built-in user could not be blocked", HTTP_409_CONFLICT, ERR),
    "USER_UNBLOCK_ERROR": ("Only superuser can unblock user.", HTTP_403_FORBIDDEN, ERR),
    "JOB_TERMINATION_ERROR": ("Can't terminate job", HTTP_409_CONFLICT, ERR),
    "USER_PASSWORD_ERROR": ("Password doesn't feet requirements", HTTP_409_CONFLICT, ERR),
    "USER_PASSWORD_TOO_SHORT_ERROR": ("This password is shorter than min password length", HTTP_400_BAD_REQUEST, ERR),
    "USER_PASSWORD_TOO_LONG_ERROR": ("This password is longer than max password length", HTTP_400_BAD_REQUEST, ERR),
    "USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR": (
        'Field "current_password" should be filled and match user current password',
        HTTP_400_BAD_REQUEST,
        ERR,
    ),
    "BAD_REQUEST": ("Bad request", HTTP_400_BAD_REQUEST, ERR),
    "HOSTPROVIDER_CREATE_ERROR": ("Error during process of host provider creating", HTTP_409_CONFLICT, ERR),
    "CONFIG_OPTION_ERROR": ("error in config option type", HTTP_409_CONFLICT, ERR),
    "DATABASE_IS_LOCKED": ("SQLite not for production", HTTP_500_INTERNAL_SERVER_ERROR, ERR),
    "UNPROCESSABLE_ENTITY": ("Can't process data", HTTP_422_UNPROCESSABLE_ENTITY, ERR),
    "CREATE_CONFLICT": ("Can't create object", HTTP_409_CONFLICT, ERR),
    "HOST_GROUP_CONFLICT": ("Can't change hosts in group", HTTP_409_CONFLICT, ERR),
    "BUNDLE_SIGNATURE_VERIFICATION_ERROR": ("Bundle signature verification error", HTTP_409_CONFLICT, ERR),
    "WRONG_OWNER": ("Incorrect owner", HTTP_409_CONFLICT, ERR),
}


def get_error(code):
    if code in ERRORS:
        err = ERRORS[code]
        if len(err) == 1:
            return code, err[0], HTTP_404_NOT_FOUND, ERR
        elif len(err) == 2:
            return code, err[0], err[1], ERR
        else:
            return code, err[0], err[1], err[2]
    else:
        msg = f'unknown error: "{code}"'

        return "UNKNOWN_ERROR", msg, HTTP_501_NOT_IMPLEMENTED, CRIT


class AdcmEx(APIException):
    def __init__(self, code, msg="", http_code: int | None = None, args=""):
        err_code, err_msg, err_http_code, level = get_error(code)
        if msg != "":
            err_msg = msg

        if http_code is not None:
            err_http_code = http_code

        self.msg = err_msg
        self.level = level
        self.code = err_code
        self.status_code = err_http_code
        detail = {
            "code": err_code,
            "level": level,
            "desc": err_msg,
        }
        if err_code == "UNKNOWN_ERROR":
            detail["args"] = code
        elif args:
            detail["args"] = args

        super().__init__(detail, err_http_code)

    def __str__(self):
        return self.msg


def raise_adcm_ex(code, msg="", args=""):
    _, err_msg, _, _ = get_error(code)
    if msg != "":
        err_msg = msg

    logger.error(err_msg)

    raise AdcmEx(code, msg=msg, args=args)


def custom_drf_exception_handler(exc: Exception, context) -> Response | None:
    if isinstance(exc, OverflowError):
        # This is an error with DB mostly. For example SQLite can't handle 64-bit numbers.
        # So we have to handle this right and rise HTTP 400, instead of HTTP 500

        return exception_handler(exc=AdcmEx(code="OVERFLOW"), context=context)

    if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
        msg = ""
        for field_name, error in exc.detail.items():
            if isinstance(error, list):
                if isinstance(error[0], dict):
                    for err_type, err in error[0].items():
                        msg = f"{msg}{err_type} - {err[0]};"
                else:
                    msg = f"{msg}{field_name} - {error[0]};"
            else:
                for err_type, err in error.items():
                    msg = f"{msg}{err_type} - {err[0]};"

        return exception_handler(exc=AdcmEx(code="BAD_REQUEST", msg=msg), context=context)

    if (
        isinstance(exc, OperationalError)
        and settings.DB_DEFAULT["ENGINE"] == "django.db.backends.sqlite3"
        and str(exc) == "database is locked"
    ):
        return exception_handler(
            exc=AdcmEx(
                code="DATABASE_IS_LOCKED",
                msg=(
                    "Something wrong\n"
                    '<a href="https://docs.arenadata.io/en/ADCM/current/get-started/external-db.html">'
                    "SQLite not for production use</a>"
                ),
            ),
            context=context,
        )

    return exception_handler(exc=exc, context=context)
