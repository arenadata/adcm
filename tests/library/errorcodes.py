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

"""Tools for ADCM errors handling in tests"""

from typing import Iterable, List

import pytest_check as check
from adcm_client.wrappers.api import ADCMApiError
from coreapi.exceptions import ErrorMessage
from pytest_check.check_methods import get_failures


class ADCMError:
    """
    ADCM error wrapper
    Used for error assertions
    """

    def __init__(self, title, code):
        self.title = title
        self.code = code
        self._special_comparators = {ADCMApiError: self._compare_adcm_api_error}

    def equal(self, e, *args):
        """Assert error properties"""
        for err_class, comparator in self._special_comparators.items():
            if e.__class__ is err_class or issubclass(e.__class__, err_class):
                comparator(e, *args)
                return
        self._compare_error_message(e, *args)

    def _compare_error_message(self, e: ErrorMessage, *args):
        error = e.value.error if hasattr(e, 'value') else e.error
        title = error.title
        code = error.get("code", "")
        desc = error.get("desc", "")
        error_args = error.get("args", "")
        check.equal(title, self.title, f'Expected title is "{self.title}", actual is "{title}"')
        check.equal(code, self.code, f'Expected error code is "{self.code}", actual is "{code}"')
        for i in args:
            err_msg = 'Unknown'
            check.is_true(
                i in desc or i in error_args or i in (err_msg := self._get_data_err_messages(error)),
                (
                    f"Text '{i}' should be present in error message. Either in:\n"
                    f'Description: {desc}\n'
                    f'Error arguments: {error_args}\n'
                    f'Or message: {err_msg}'
                ),
            )
        assert not get_failures(), "All assertions should passed"

    def _compare_adcm_api_error(self, e: ADCMApiError, *_):
        code, *_ = e.args
        assert self.code == code, f"Error expected to be {self.code}, not {code}"

    def _get_data_err_messages(self, error) -> List[str]:
        """Extract all messages from _data attribute or an error if it is presented"""
        data = getattr(error, '_data', None)
        if data is None:
            return []
        if isinstance(data, dict):
            messages = []
            for val in data.values():
                if isinstance(val, str):
                    messages.append(val)
                elif isinstance(val, Iterable):
                    messages.extend(val)
                else:
                    messages.append(val)
            return messages
        raise ValueError('error._dict expected to be dict instance')

    def __str__(self):
        return f'{self.code} {self.title}'


INVALID_OBJECT_DEFINITION = ADCMError(
    '409 Conflict',
    'INVALID_OBJECT_DEFINITION',
)

INVALID_CONFIG_DEFINITION = ADCMError(
    '409 Conflict',
    'INVALID_CONFIG_DEFINITION',
)

UPGRADE_ERROR = ADCMError(
    '409 Conflict',
    'UPGRADE_ERROR',
)

BUNDLE_ERROR = ADCMError(
    '409 Conflict',
    'BUNDLE_ERROR',
)

BUNDLE_CONFLICT = ADCMError(
    '409 Conflict',
    'BUNDLE_CONFLICT',
)

UPGRADE_NOT_FOUND = ADCMError(
    '404 Not Found',
    'UPGRADE_NOT_FOUND',
)

CONFIG_VALUE_ERROR = ADCMError(
    '400 Bad Request',
    'CONFIG_VALUE_ERROR',
)

CONFIG_KEY_ERROR = ADCMError(
    '400 Bad Request',
    'CONFIG_KEY_ERROR',
)

GROUP_CONFIG_HOST_ERROR = ADCMError(
    '400 Bad Request',
    'GROUP_CONFIG_HOST_ERROR',
)

GROUP_CONFIG_HOST_EXISTS = ADCMError(
    '400 Bad Request',
    'GROUP_CONFIG_HOST_EXISTS',
)

ATTRIBUTE_ERROR = ADCMError(
    '400 Bad Request',
    'ATTRIBUTE_ERROR',
)

TASK_ERROR = ADCMError(
    '409 Conflict',
    'TASK_ERROR',
)

GROUP_CONFIG_CHANGE_UNSELECTED_FIELD = ADCMError(
    '400 Bad Request',
    'GROUP_CONFIG_CHANGE_UNSELECTED_FIELD',
)

STACK_LOAD_ERROR = ADCMError(
    '409 Conflict',
    'STACK_LOAD_ERROR',
)

DEFINITION_KEY_ERROR = ADCMError(
    '409 Conflict',
    'DEFINITION_KEY_ERROR',
)

INVALID_UPGRADE_DEFINITION = ADCMError(
    '409 Conflict',
    'INVALID_UPGRADE_DEFINITION',
)

INVALID_VERSION_DEFINITION = ADCMError(
    '409 Conflict',
    'INVALID_VERSION_DEFINITION',
)

INVALID_ACTION_DEFINITION = ADCMError(
    '409 Conflict',
    'INVALID_ACTION_DEFINITION',
)

JSON_ERROR = ADCMError(
    '400 Bad Request',
    'JSON_ERROR',
)

FOREIGN_HOST = ADCMError(
    '409 Conflict',
    'FOREIGN_HOST',
)

PROTOTYPE_NOT_FOUND = ADCMError(
    '404 Not Found',
    'PROTOTYPE_NOT_FOUND',
)

CONFIG_NOT_FOUND = ADCMError(
    '404 Not Found',
    'CONFIG_NOT_FOUND',
)

PROVIDER_NOT_FOUND = ADCMError(
    '404 Not Found',
    'PROVIDER_NOT_FOUND',
)

HOST_NOT_FOUND = ADCMError(
    '404 Not Found',
    'HOST_NOT_FOUND',
)

CLUSTER_NOT_FOUND = ADCMError(
    '404 Not Found',
    'CLUSTER_NOT_FOUND',
)

CLUSTER_SERVICE_NOT_FOUND = ADCMError(
    '404 Not Found',
    'CLUSTER_SERVICE_NOT_FOUND',
)

SERVICE_NOT_FOUND = ADCMError(
    '404 Not Found',
    'SERVICE_NOT_FOUND',
)

HOSTSERVICE_NOT_FOUND = ADCMError(
    '404 Not Found',
    'HOSTSERVICE_NOT_FOUND',
)

TASK_GENERATOR_ERROR = ADCMError(
    '409 Conflict',
    'TASK_GENERATOR_ERROR',
)

SERVICE_CONFLICT = ADCMError(
    '409 Conflict',
    'SERVICE_CONFLICT',
)

HOST_CONFLICT = ADCMError(
    '409 Conflict',
    'HOST_CONFLICT',
)

CLUSTER_CONFLICT = ADCMError(
    '409 Conflict',
    'CLUSTER_CONFLICT',
)

PROVIDER_CONFLICT = ADCMError(
    '409 Conflict',
    'PROVIDER_CONFLICT',
)

WRONG_NAME = ADCMError(
    '400 Bad Request',
    'WRONG_NAME',
)

BIND_ERROR = ADCMError(
    '409 Conflict',
    'BIND_ERROR',
)

MAINTENANCE_MODE_NOT_AVAILABLE = ADCMError(
    '409 Conflict',
    'MAINTENANCE_MODE_NOT_AVAILABLE',
)

ACTION_ERROR = ADCMError(
    '409 Conflict',
    'ACTION_ERROR',
)


INVALID_HC_HOST_IN_MM = ADCMError(
    '409 Conflict',
    'INVALID_HC_HOST_IN_MM',
)

USER_UPDATE_ERROR = ADCMError('400 Bad Request', 'USER_UPDATE_ERROR')

GROUP_UPDATE_ERROR = ADCMError('400 Bad Request', 'GROUP_UPDATE_ERROR')

# ADCMApiError
AUTH_ERROR = ADCMError('400 Bad Request', 'AUTH_ERROR')

COMPONENT_CONSTRAINT_ERROR = ADCMError(
    '409 Conflict',
    'COMPONENT_CONSTRAINT_ERROR',
)
