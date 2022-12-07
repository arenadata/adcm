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
"""
Utility functions for ADCM upgrade process
"""
from typing import Tuple

import allure
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.docker_utils import ADCM
from version_utils import rpm


@allure.step("Check that ADCM version has been changed")
def check_adcm_version_changed(before: str, after: str) -> None:
    """Check if 'after' version is more recent that 'before'"""
    if rpm.compare_versions(after, before) < 1:
        raise AssertionError("ADCM version after upgrade is older or equal to the version before")


@allure.step("Upgrade ADCM to new version")
def upgrade_adcm_version(adcm: ADCM, sdk: ADCMClient, credentials: dict, target: Tuple[str, str]) -> None:
    """
    Upgrade ADCM via ADCMClient (stop running container, launch container with new version)
    and check that version has changed
    """
    buf = sdk.adcm_version
    adcm.upgrade(target)
    sdk.reset(url=adcm.url, **credentials)
    check_adcm_version_changed(buf, sdk.adcm_version)
