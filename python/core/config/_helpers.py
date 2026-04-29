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
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")


def recursive_defaultdict():
    return defaultdict(recursive_defaultdict)


def recursive_defaultdict_to_dict(d: defaultdict[K, V]) -> dict[K, V]:
    return {k: recursive_defaultdict_to_dict(v) if isinstance(v, defaultdict) else v for k, v in d.items()}
