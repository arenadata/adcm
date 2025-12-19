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

from types import NoneType
from typing import Any, Generic, Protocol, TypeGuard, TypeVar

T = TypeVar("T", contravariant=True)


class Predicate(Generic[T], Protocol):
    def __call__(self, arg: T, /) -> bool:
        ...


def always(_: Any) -> bool:
    return True


def never(_: Any) -> bool:
    return False


def is_none(arg: Any) -> TypeGuard[NoneType]:
    return arg is None


def is_not_none(arg: Any) -> bool:
    return not is_none(arg)


def is_non_empty_string(arg: Any) -> TypeGuard[str]:
    return is_str(arg) and arg != ""


def is_str(arg: Any) -> TypeGuard[str]:
    return isinstance(arg, str)
