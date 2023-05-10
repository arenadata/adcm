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

from typing import Any


class Empty:
    """Same as None but useful when None is valid value"""

    def __bool__(self):
        return False


def set_not_empty_attr(obj, partial: bool, attr: str, value: Any, default: Any | None = None) -> None:
    if partial:
        if value is not Empty:
            setattr(obj, attr, value)
    else:
        value = value if value is not Empty else default
        setattr(obj, attr, value)


def get_query_tuple_str(tuple_items: set | tuple) -> str:
    tuple_str = "("
    for item in tuple_items:
        tuple_str = f"{tuple_str}{item},"

    return f"{tuple_str[:-1]})"
