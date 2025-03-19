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

from functools import wraps
from typing import Callable, TypeVar

from core.bundle_alt.errors import BundleParsingError, BundleProcessingError, BundleValidationError
from core.errors import ConfigValueError
from core.types import ADCMComposableError

from cm.errors import AdcmEx

T = TypeVar("T", bound=Callable)


def convert_bundle_errors_to_adcm_ex(func: T) -> T:
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BundleProcessingError as e:
            http_code = 409
            error_code = "BUNDLE_ERROR"
            message = e.message
            raise AdcmEx(msg=message, code=error_code, http_code=http_code) from e
        except BundleParsingError as e:
            http_code = 409
            error_code = "BUNDLE_DEFINITION_ERROR"
            message = _prepare_message_from_composable(e)
            raise AdcmEx(msg=message, code=error_code, http_code=http_code) from e
        except BundleValidationError as e:
            http_code = 409
            error_code = "BUNDLE_VALIDATION_ERROR"
            message = _prepare_message_from_composable(e)
            raise AdcmEx(msg=message, code=error_code, http_code=http_code) from e
        except ConfigValueError as e:
            http_code = 409
            error_code = e.code
            message = e.msg
            raise AdcmEx(msg=message, code=error_code, http_code=http_code) from e

    return wrapped


def _prepare_message_from_composable(err: ADCMComposableError) -> str:
    return err.message
