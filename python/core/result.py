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

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, Generic, Literal, ParamSpec, TypeGuard, TypeVar

T = TypeVar("T")
V = TypeVar("V")
P = ParamSpec("P")
Exc = TypeVar("Exc", bound=Exception)

# Success / Fail


@dataclass(slots=True)
class Success(Generic[T]):
    value: T

    def __bool__(self) -> Literal[True]:
        return True


@dataclass(slots=True)
class Fail(Generic[T]):
    value: T

    def __bool__(self) -> Literal[False]:
        return False


def is_success(result: Success[T] | Fail) -> TypeGuard[Success[T]]:
    return bool(result)


def is_fail(result: Success | Fail[T]) -> TypeGuard[Fail[T]]:
    return not is_success(result)


# Working with errors


def fail_with_call_on_error(on_error: Callable[[Exception], V]) -> Callable[[Callable[P, T]], Callable[P, T | Fail[V]]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T | Fail[V]]:
        @wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T | Fail[V]:
            try:
                return func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                return Fail(on_error(e))

        return wrapped

    return decorator


def log_and_ignore(error: Exc, log_func: Callable[[Exc], Any]) -> Exc:
    log_func(error)
    return error
