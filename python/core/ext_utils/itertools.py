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

from collections import defaultdict
from typing import Callable, Generator, Iterable, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def to_pairs(iterable: Iterable[V], *, key: Callable[[V], K]) -> Generator[tuple[K, V], None, None]:
    """
    Return pairs (tuples of two) based on given iterable
    """
    return ((key(v), v) for v in iterable)


def group_by(iterable: Iterable[V], *, key: Callable[[V], K]) -> dict[K, list[V]]:
    """
    Relative of `itertools.groupby` grouping by custom key into intermediate dict (=> sorting is not required).
    """

    result = defaultdict(list)

    for k, v in to_pairs(iterable, key=key):
        result[k].append(v)

    return result
