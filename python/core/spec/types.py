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

from typing import NewType

FullSpecKey = NewType("FullSpecKey", str)
"""
"Flat" key of an entry, each level is prefixed with `/`.
Entries at "root" of a specification are keyed like `"/entry"`, `"/group"`,
and entries inside groups `"/group/entry"`.

Build it via `core.spec.keys`, not by calling `FullSpecKey` directly:
the constructor performs no checks, so it can't guarantee the leading `/`.
"""

LevelSpecKey = NewType("LevelSpecKey", str)
"""
Key of an entry, unique inside one hierarchy level (root or group).
Doesn't contain `/`, it's just the name of an entry.
"""

KEY_SEPARATOR = "/"
KEY_ROOT_PREFIX = "/"
"""
Prefix to put before the first level key
"""
