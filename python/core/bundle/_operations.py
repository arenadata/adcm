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

from adcm_version import compare_adcm_versions

from core.bundle._errors import BundleParsingError


def check_adcm_min_version(current: str, required: str) -> None:
    if compare_adcm_versions(required, current) > 0:
        raise BundleParsingError(
            f"This bundle required ADCM version equal to {required} or newer.",
        )
