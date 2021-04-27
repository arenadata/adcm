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
from delayed_assert import expect, assert_expectations


class ADCMError():
    def __init__(self, title, code):
        self.title = title
        self.code = code

    def equal(self, e, *args):
        title = e.value.error.title
        code = e.value.error.get("code", "")
        desc = e.value.error.get("desc", "")
        error_args = e.value.error.get("args", "")
        expect(
            title == self.title,
            f'Expected title is "{self.title}", actual is "{title}"'
        )
        expect(
            code == self.code,
            f'Expected error code is "{self.code}", actual is "{code}"'
        )
        for i in args:
            expect(
                i in desc or i in error_args,
                f'Expected part of desc or args is "{i}", '
                f'actual desc is: \n"{desc}", '
                f'\nargs is: \n"{error_args or None}"'
            )
        assert_expectations()


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

TASK_ERROR = ADCMError(
    '409 Conflict',
    'TASK_ERROR',
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

LONG_NAME = ADCMError(
    '400 Bad Request',
    'LONG_NAME',
)

WRONG_NAME = ADCMError(
    '400 Bad Request',
    'WRONG_NAME',
)

BIND_ERROR = ADCMError(
    '409 Conflict',
    'BIND_ERROR',
)
