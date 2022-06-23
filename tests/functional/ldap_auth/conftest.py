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

"""Conftest for LDAP-related tests"""

from pathlib import Path
from typing import Generator, Optional

import allure
import ldap
import pytest
import yaml
from _pytest.fixtures import SubRequest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Group, User

from tests.api.utils.tools import random_string
from tests.library.ldap_interactions import LDAPTestConfig, LDAPEntityManager
from tests.library.utils import ConfigError

# pylint: disable=redefined-outer-name

LDAP_PREFIX = 'ldap://'
LDAPS_PREFIX = 'ldaps://'
BASE_BUNDLES_DIR = Path(__file__).parent / 'bundles'


@allure.title('[SS] Get LDAP config')
@pytest.fixture(scope='session')
def ldap_config(cmd_opts) -> dict:
    """
    Load LDAP config from file as a dictionary.
    Returns empty dict if `--ldap-conf` is not presented.
    """
    if not cmd_opts.ldap_conf:
        return {}
    config_fp = Path(cmd_opts.ldap_conf)
    if not config_fp.exists():
        raise ConfigError(f'Path to LDAP config file should exist: {config_fp}')
    with config_fp.open('r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ConfigError('LDAP config file should have root type "dict"')
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # pylint: disable=no-member
    return config


@allure.title('[SS] Extract AD config')
@pytest.fixture(scope='session')
def ad_config(ldap_config: dict) -> LDAPTestConfig:
    """Create AD config from config file"""
    required_keys = {'uri', 'admin_dn', 'admin_pass', 'base_ou_dn'}
    if 'ad' not in ldap_config:
        raise ConfigError('To test LDAP with AD LDAP config file should have "ad" key')
    config = ldap_config['ad']
    if not required_keys.issubset(config.keys()):
        raise ConfigError(
            'Not all required keys are presented in "ad" LDAP config.\n'
            f'Required: {required_keys}\n'
            f'Actual: {config.keys()}'
        )
    return LDAPTestConfig(
        config['uri'],
        config['admin_dn'],
        config['admin_pass'],
        config['base_ou_dn'],
        config.get('cert', None),
    )


@allure.title('Prepare LDAP entities manager')
@pytest.fixture()
def ldap_ad(request: SubRequest, ad_config) -> Generator[LDAPEntityManager, None, None]:
    """Create LDAP entities manager from AD config"""
    with LDAPEntityManager(ad_config, request.node.nodeid) as ldap_manager:
        yield ldap_manager


@allure.title('Create basic OUs for testing')
@pytest.fixture()
def ldap_basic_ous(ldap_ad):
    """Get LDAP group (ou) DNs for groups and users"""
    groups_ou_dn = ldap_ad.create_ou('groups-main')
    users_ou_dn = ldap_ad.create_ou('users-main')
    return groups_ou_dn, users_ou_dn


@allure.title('Create LDAP user without group')
@pytest.fixture()
def ldap_user(ldap_ad, ldap_basic_ous) -> dict:
    """Create LDAP AD user"""
    user = {'name': f'user_wo_group_{random_string(6)}', 'password': random_string(12)}
    _, users_dn = ldap_basic_ous
    user['dn'] = ldap_ad.create_user(**user, custom_base_dn=users_dn)
    return user


@allure.title('Create LDAP group')
@pytest.fixture()
def ldap_group(ldap_ad, ldap_basic_ous) -> dict:
    """Create LDAP AD group for adding users"""
    group = {'name': 'adcm_users'}
    groups_dn, _ = ldap_basic_ous
    group['dn'] = ldap_ad.create_group(**group, custom_base_dn=groups_dn)
    return group


@allure.title('Create LDAP user in group')
@pytest.fixture()
def ldap_user_in_group(ldap_ad, ldap_basic_ous, ldap_group) -> dict:
    """Create LDAP AD user and add it to a default "allowed to log to ADCM" group"""
    user = {'name': f'user_in_group_{random_string(6)}', 'password': random_string(12)}
    _, users_dn = ldap_basic_ous
    user['dn'] = ldap_ad.create_user(**user, custom_base_dn=users_dn)
    ldap_ad.add_user_to_group(user['dn'], ldap_group['dn'])
    return user


@pytest.fixture()
def ad_ssl_cert(adcm_fs, ad_config) -> Optional[Path]:
    """Put SSL certificate from config to ADCM container and return path to it"""
    if ad_config.cert is None:
        return None
    path = Path('/adcm/.ad-cert')
    result = adcm_fs.container.exec_run(['sh', '-c', f'echo "{ad_config.cert}" > {path}'])
    if result.exit_code != 0:
        raise ValueError('Failed to upload AD certificate to ADCM')
    return path


@allure.title('Configure ADCM for LDAP (AD) integration')
@pytest.fixture(params=[False], ids=['ssl_off'])
def configure_adcm_ldap_ad(request, sdk_client_fs: ADCMClient, ldap_basic_ous, ad_config, ad_ssl_cert):
    """Configure ADCM to allow AD users"""
    ssl_on = request.param
    ssl_extra_config = {}
    groups_ou, users_ou = ldap_basic_ous

    # we suggest that configuration is right
    if ssl_on:
        if ad_config.uri.startswith(LDAP_PREFIX):
            ad_config.uri.replace(LDAP_PREFIX, LDAPS_PREFIX)
        if ad_ssl_cert is None:
            raise ConfigError('AD SSL cert should be uploaded to ADCM')
        ssl_extra_config['tls_ca_cert_file'] = str(ad_ssl_cert)
    elif not ssl_on and ad_config.uri.startswith(LDAPS_PREFIX):
        ad_config.uri.replace(LDAPS_PREFIX, LDAP_PREFIX)

    adcm = sdk_client_fs.adcm()
    adcm.config_set_diff(
        {
            'attr': {'ldap_integration': {'active': True}},
            'config': {
                'ldap_integration': {
                    'ldap_uri': ad_config.uri,
                    'ldap_user': ad_config.admin_dn,
                    'ldap_password': ad_config.admin_pass,
                    'user_search_base': users_ou,
                    'group_search_base': groups_ou,
                    **ssl_extra_config,
                }
            },
        }
    )


def get_ldap_user_from_adcm(client: ADCMClient, name: str) -> User:
    """
    Get LDAP user from ADCM.
    Name should be sAMAccount value.
    :raises AssertionError: when there's no user presented in ADCM
    """
    username = name.lower()
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
        return client.group(name=name)
    except ObjectNotFound as e:
        raise AssertionError(f'LDAP group "{name}" should be available as ADCM group "{name}"') from e
