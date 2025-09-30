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

from dataclasses import dataclass
from typing import Generic, Literal, TypeGuard, TypeVar

T = TypeVar("T")


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
