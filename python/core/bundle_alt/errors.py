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

from collections import defaultdict, deque
from functools import wraps
from itertools import filterfalse

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from core.types import ADCMLocalizedError, ADCMMessageError


class BundleProcessingError(ADCMMessageError):
    """
    Use for errors that breaks further processing of bundle
    """


class BundleParsingError(ADCMLocalizedError):
    """
    Use for errors occured during parsing and structural validation of bundle's definitions
    """


class BundleValidationError(ADCMLocalizedError):
    """
    Use for errors in objects relations and overall "sanity" of bundle definitions
    """


def convert_validation_to_bundle_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            grouped_errors = _group_validation_errors(e.errors(include_url=False))
            details = _render_message(grouped_errors, level=())

            prefix = "Errors found in definition of bundle entity:"
            message = f"{prefix}\n{details}"

            raise BundleParsingError(message) from e

    return wrapped


def _group_validation_errors(errors: list[ErrorDetails]) -> dict:
    result = _recursive_defaultdict()

    for error in errors:
        location = _get_error_location(error["loc"])

        node = result
        for part in location:
            node = node["fields"][part]

        errors = node.setdefault("errors", deque())
        errors.append(error)

    return result


def _render_message(grouped_errors: dict, level: tuple[str, ...]) -> str:
    level_indent = " " * len(level)
    error_indent = f"{level_indent}| "

    errors_at_level = set()

    for err in grouped_errors.get("errors", ()):
        err_message = f"{error_indent}{err['type']}: {err['msg']}"
        errors_at_level.add(err_message)

    message = ""
    level_block = f"{level_indent}{level[-1] if level else ''}"

    if errors_at_level:
        error_block = "\n".join(sorted(errors_at_level))
        message = f"{level_block}\n{error_block}"

    next_level_fields = grouped_errors.get("fields", {})
    if not next_level_fields:
        return message

    if not message:
        message = level_block

    next_level_messages = deque()

    for next_level, next_level_error in next_level_fields.items():
        next_message = _render_message(next_level_error, level=(*level, next_level))
        next_level_messages.append(next_message)

    if next_level_messages:
        next_level_message = "\n".join(filter(bool, next_level_messages))
        message = f"{message}\n{next_level_message}" if message else next_level_message

    return message


def _get_error_location(loc: tuple[int | str, ...]) -> tuple[str, ...]:
    return tuple(filterfalse(_is_function_step, map(str, loc)))


def _is_function_step(x):
    return x.startswith("function-")


def _recursive_defaultdict():
    return defaultdict(_recursive_defaultdict)
