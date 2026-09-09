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

from collections.abc import Callable, Iterable
from itertools import chain

from pydantic_core import ErrorDetails

from core.ext_utils.itertools import group_by


def get_type(details: ErrorDetails) -> str:
    return details["type"]


def pydantic_err_location_to_str(
    error: ErrorDetails,
    *,
    separator: str = "/",
    start_with_separator: bool = True,
) -> str:
    joined = separator.join(map(str, error["loc"]))
    if start_with_separator:
        return f"{separator}{joined}"

    return joined


def pydantic_err_to_point_only_location(error: ErrorDetails) -> str:
    return f"- {pydantic_err_location_to_str(error)}"


def pydantic_err_to_point_with_type(error: ErrorDetails) -> str:
    return f"{pydantic_err_to_point_only_location(error)} ({error['type']})"


def format_pydantic_errors(
    errors: Iterable[ErrorDetails],
    convert: Callable[[ErrorDetails], str],
    *,
    separator: str = "\n",
    prefix: str = "",
    suffix: str = "",
) -> str:
    errors_repr = separator.join(map(convert, errors))
    return f"{prefix}{errors_repr}{suffix}"


def represent_missing_and_others_errors_without_description(
    errors: Iterable[ErrorDetails],
    prefix: str,
    *,
    blocks_separator: str = "\n",
) -> str:
    """
    Prepare message that contains prefix and at most two blocks:
    1. Missing keys (with err locations).
    2. Other errors (with err location and type).
    This function is designed to be used when contents of pydantic errors are too much (e.g. security cases).
    """
    grouped_errors = group_by(errors, key=get_type)
    missing = grouped_errors.pop("missing", [])
    others = list(chain.from_iterable(grouped_errors.values()))

    message = prefix
    if missing:
        missing_keys_repr = format_pydantic_errors(
            errors=missing,
            convert=pydantic_err_to_point_only_location,
            prefix=f"{blocks_separator}Following keys are missing:{blocks_separator}",
        )
        message += missing_keys_repr

    if others:
        other_errors_repr = format_pydantic_errors(
            errors=others,
            convert=pydantic_err_to_point_with_type,
            prefix=f"{blocks_separator}Other validation errors:{blocks_separator}",
        )
        message += other_errors_repr

    return message
