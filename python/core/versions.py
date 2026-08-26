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

from typing import Protocol

from adcm_version import compare_prototype_versions


class ObjectWithVersions(Protocol):
    @property
    def min_version(self) -> str:
        ...

    @property
    def max_version(self) -> str:
        ...

    @property
    def min_strict(self) -> bool:
        ...

    @property
    def max_strict(self) -> bool:
        ...


def is_version_suitable(version: str, versions_object: ObjectWithVersions) -> bool:
    if (
        versions_object.min_strict
        and compare_prototype_versions(version, versions_object.min_version) <= 0
        or versions_object.min_version
        and compare_prototype_versions(version, versions_object.min_version) < 0
    ):
        return False

    if (
        versions_object.max_strict
        and compare_prototype_versions(version, versions_object.max_version) >= 0
        or versions_object.max_version
        and compare_prototype_versions(version, versions_object.max_version) > 0
    ):
        return False

    return True
