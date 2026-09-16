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

from collections.abc import Iterable

from core.spec.errors import InvalidSpecKeyError
from core.spec.types import KEY_ROOT_PREFIX, KEY_SEPARATOR, FullSpecKey, LevelSpecKey


def to_full_key(raw: str) -> FullSpecKey:
    """
    Build a full key out of a string that is expected to already be one.

    Unlike `ensure_full_key` it doesn't repair the input: absence of the root prefix
    means the caller got something that isn't a full key, which is worth knowing at the boundary
    rather than after the (silently renamed) key fails to match anything.
    """

    if not raw.startswith(KEY_ROOT_PREFIX):
        message = f"Full key is expected to start with {KEY_ROOT_PREFIX!r}, got {raw!r}"
        raise InvalidSpecKeyError(message)

    return FullSpecKey(raw)


def ensure_full_key(key: str) -> FullSpecKey:
    key_ = key.rstrip(KEY_SEPARATOR)

    if not key_.startswith(KEY_ROOT_PREFIX):
        return FullSpecKey(f"{KEY_ROOT_PREFIX}{key_}")

    return FullSpecKey(key_)


def full_key_to_level_keys(full: FullSpecKey) -> tuple[LevelSpecKey, ...]:
    return tuple(LevelSpecKey(level) for level in full.split(KEY_SEPARATOR) if level)


def full_key_without_root_prefix(full: FullSpecKey) -> str:
    # sometimes it's required to have full key without leading separator,
    # mostly for plugins / old APIs
    return ensure_full_key(full).removeprefix(KEY_ROOT_PREFIX)


def level_keys_to_full_key(levels: Iterable[LevelSpecKey]) -> FullSpecKey:
    return ensure_full_key(KEY_SEPARATOR.join(levels))


def level_keys_to_full_key_safe(levels: Iterable[LevelSpecKey | None]) -> FullSpecKey:
    non_empty_strings: Iterable[LevelSpecKey] = (level for level in levels if level)
    return level_keys_to_full_key(non_empty_strings)


def level_key_from_full_key(full: FullSpecKey) -> LevelSpecKey:
    *_, key = full.rsplit(KEY_SEPARATOR, maxsplit=1)
    return LevelSpecKey(key)


def join_full_key_with_group_key(full: FullSpecKey, group: LevelSpecKey) -> FullSpecKey:
    return ensure_full_key(f"{group}{full}")


def join_level_key_with_group_key(key: LevelSpecKey, group: FullSpecKey) -> FullSpecKey:
    return ensure_full_key(f"{group}{KEY_SEPARATOR}{key}")


def remove_group_from_key(key: FullSpecKey, group: FullSpecKey) -> FullSpecKey:
    return FullSpecKey(key.removeprefix(group))


def is_part_of_group(key: FullSpecKey, group: FullSpecKey) -> bool:
    return key.startswith(f"{group}{KEY_SEPARATOR}")
