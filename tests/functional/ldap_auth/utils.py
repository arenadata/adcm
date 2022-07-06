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

"""Utilities for LDAP-related tests"""

from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Group, User


SYNC_ACTION_NAME = 'run_ldap_sync'


def get_ldap_user_from_adcm(client: ADCMClient, name: str) -> User:
    """
    Get LDAP user from ADCM.
    Name should be sAMAccount value.
    :raises AssertionError: when there's no user presented in ADCM
    """
    username = name
    try:
        return client.user(username=username)
    except ObjectNotFound as e:
        raise AssertionError(f'LDAP user "{name}" should be available as ADCM "{username}" user') from e


def get_ldap_group_from_adcm(client: ADCMClient, name: str) -> Group:
    """
    Get LDAP group from ADCM.
    :raises AssertionError: when there's no group presented in ADCM
    """
    try:
        return client.group(name=name, type='ldap')
    except ObjectNotFound as e:
        raise AssertionError(f'LDAP group "{name}" should be available as ADCM group "{name}"') from e
