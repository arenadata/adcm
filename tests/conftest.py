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

"""Common fixtures and tools for ADCM tests"""

# pylint: disable=W0621
import os
import pathlib
import sys
import tarfile
from pathlib import PosixPath
from typing import Generator, List, Optional, Tuple, Union

import allure
import ldap
import pytest
import websockets.client
import yaml
from _pytest.python import Function, FunctionDefinition, Module
from adcm_client.objects import ADCMClient, Bundle, Cluster, Provider, User
from adcm_pytest_plugin.docker.adcm import ADCM
from adcm_pytest_plugin.docker.launchers import ADCMWithPostgresLauncher
from adcm_pytest_plugin.utils import random_string
from allure_commons.model2 import Parameter, TestResult
from allure_pytest.listener import AllureListener
from docker.utils import parse_repository_tag
from tests.library.adcm_websockets import ADCMWebsocket
from tests.library.api.client import APIClient
from tests.library.db import PostgreSQLQueryExecutioner, QueryExecutioner
from tests.library.ldap_interactions import (
    LDAPEntityManager,
    LDAPTestConfig,
    configure_adcm_for_ldap,
)
from tests.library.utils import ConfigError

pytest_plugins = "adcm_pytest_plugin"  # pylint: disable=invalid-name

# We have a number of calls from functional or ui_tests to cm module,
# so we need a way to extend PYTHONPATH at test time.
testdir = os.path.dirname(__file__)
rootdir = os.path.dirname(testdir)
pythondir = os.path.abspath(os.path.join(rootdir, "python"))
sys.path.append(pythondir)

# can be used to dump it to file to create dummy bundle archives
DUMMY_CLUSTER_BUNDLE = [
    {
        "type": "cluster",
        "name": "test_cluster",
        "description": "community description",
        "version": "1.5",
        "edition": "community",
    }
]
DUMMY_ACTION = {
    "dummy_action": {
        "type": "job",
        "script": "./actions.yaml",
        "script_type": "ansible",
        "states": {"available": "any"},
    }
}

CHROME_PARAM = pytest.param("Chrome")
FIREFOX_PARAM = pytest.param("Firefox", marks=[pytest.mark.full])
ONLY_CHROME_PARAM = [CHROME_PARAM]
CHROME_AND_FIREFOX_PARAM = [CHROME_PARAM, FIREFOX_PARAM]
INCLUDE_FIREFOX_MARK = "include_firefox"

TEST_USER_CREDENTIALS = "test_user", "password"


def _marker_in_node(mark: str, node: Union[FunctionDefinition, Module]) -> bool:
    """Check if mark is in own_markers of a node"""
    return any(marker.name == mark for marker in node.own_markers)


def marker_in_node_or_its_parent(mark: str, node) -> bool:
    """Check if mark is in own_markers of a node or any of its parents"""
    marker_at_this_node = _marker_in_node(mark, node)
    if marker_at_this_node or node.parent is None:
        return marker_at_this_node
    return marker_in_node_or_its_parent(mark, node.parent)


def pytest_generate_tests(metafunc):
    """
    Parametrize web_driver fixture of browser names based on run options
    """
    if "browser" in metafunc.fixturenames:
        browsers = (
            CHROME_AND_FIREFOX_PARAM
            if marker_in_node_or_its_parent(INCLUDE_FIREFOX_MARK, metafunc.definition)
            else ONLY_CHROME_PARAM
        )
        metafunc.parametrize("browser", browsers, scope="session")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item: Function):
    """
    Pytest hook that overrides test parameters
    In case of adcm tests, parameters in allure report don't make sense unlike test ID
    So, we remove all parameters in allure report but add one parameter with test ID
    """
    yield
    _override_allure_test_parameters(item)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """Run tests with id "adcm_with_dummy_data" after everything else"""
    items.sort(key=lambda x: "adcm_with_dummy_data" in x.name)


def pytest_addoption(parser):
    """
    Additional options for ADCM testing
    """
    parser.addoption(
        "--ldap-conf",
        action="store",
        default=None,
        help=(
            """
            This option is required to run ldap-related tests.
            Value should be a path to a YAML file with content like:
              ad:
                uri: ldaps://some.ldap.server
                admin_dn: admin user DN
                admin_pass: admin password
                base_ou_dn: DN in which to create all test-related entities
                cert: plaintest of a certificate for admin user to access LDAP server securely
            """
        ),
        type=pathlib.Path,
    )


def _override_allure_test_parameters(item: Function):
    """
    Overrides all pytest parameters in allure report with test ID
    """
    listener = _get_listener_by_item_if_present(item)
    if listener:
        test_result: TestResult = listener.allure_logger.get_test(None)
        test_result.parameters = [Parameter(name="ID", value=item.callspec.id)]


def _get_listener_by_item_if_present(item: Function) -> Optional[AllureListener]:
    """
    Find AllureListener instance in pytest pluginmanager
    """
    if hasattr(item, "callspec"):
        listener: AllureListener = next(
            filter(
                lambda x: isinstance(x, AllureListener),
                item.config.pluginmanager._name2plugin.values(),  # pylint: disable=protected-access
            ),
            None,
        )
        return listener
    return None


# API Client


@pytest.fixture()
def api_client(adcm_fs, adcm_api_credentials) -> APIClient:
    return APIClient(
        adcm_fs.url, {"username": adcm_api_credentials["user"], "password": adcm_api_credentials["password"]}
    )


# Generic bundles

GENERIC_BUNDLES_DIR = pathlib.Path(__file__).parent / "generic_bundles"


@pytest.fixture()
def generic_bundle(request, sdk_client_fs) -> Bundle:
    """Upload bundle from generic bundles dir"""
    if not hasattr(request, "param") or not isinstance(request.param, str):
        raise ValueError('You should parametrize "generic_bundle" fixture with bundle dir name as string')
    return sdk_client_fs.upload_from_fs(GENERIC_BUNDLES_DIR / request.param)


@pytest.fixture()
def generic_cluster(sdk_client_fs) -> Cluster:
    """Create generic simple cluster to use as "dummy" cluster in tests"""
    bundle = sdk_client_fs.upload_from_fs(GENERIC_BUNDLES_DIR / "simple_cluster")
    return bundle.cluster_create(f"Simple Test Cluster {random_string(4)}")


@pytest.fixture()
def generic_provider(sdk_client_fs) -> Provider:
    """Create generic simple provider to use as "dummy" provider in tests"""
    bundle = sdk_client_fs.upload_from_fs(GENERIC_BUNDLES_DIR / "simple_provider")
    return bundle.provider_create(f"Simple Test Provider {random_string(4)}")


# Archives


@pytest.fixture()
def bundle_archive(request, tmp_path):
    """
    Prepare tar file from dir without using bundle packer
    """
    return _pack_bundle(request.param, tmp_path)


def _pack_bundle(stack_dir, archive_dir):
    archive_name = os.path.join(archive_dir, os.path.basename(stack_dir) + ".tar")
    with tarfile.open(archive_name, "w") as tar:
        for sub in os.listdir(stack_dir):
            tar.add(os.path.join(stack_dir, sub), arcname=sub)
    return archive_name


@pytest.fixture()
def bundle_archives(request, tmp_path) -> List[str]:
    """
    Prepare multiple bundles as in bundle_archive fixture
    """
    return [_pack_bundle(bundle_path, tmp_path) for bundle_path in request.param]


@pytest.fixture(params=[[DUMMY_CLUSTER_BUNDLE]])
def create_bundle_archives(request, tmp_path: PosixPath) -> List[str]:
    """
    Create dummy bundle archives to test pagination
    It no license required in archive type of params should be List[List[dict]]
        otherwise Tuple[List[List[dict]], str] is required

    If you need licence then `params` should be of type Tuple[List[List[dict]], str]
        where first tuple item is a list of bundle configs
        and second is path to license file (for bundles with licenses)
    ! License archive is always named 'license.txt'

    :returns: list with paths to archives
    """
    archives = []
    if isinstance(request.param, list):
        bundle_configs = request.param
        license_path = "license.txt"
    elif isinstance(request.param, tuple) and len(request.param) == 2:
        bundle_configs, license_path = request.param
    else:
        raise TypeError("Request parameter should be either List[dict] or Tuple[List[dict], str]")
    for i, config in enumerate(bundle_configs):
        archive_path = tmp_path / f"spam_bundle_{i}.tar"
        config_fp = (bundle_dir := tmp_path / f"spam_bundle_{i}") / "config.yaml"
        bundle_dir.mkdir()
        with open(config_fp, "w", encoding="utf_8") as config_file:
            yaml.safe_dump(config, config_file)
        with tarfile.open(archive_path, "w") as archive:
            archive.add(config_fp, arcname="config.yaml")
            # assume that ist is declared in first item
            if "license" in config[0]:
                license_fp = os.path.join(license_path)
                archive.add(license_fp, arcname=config[0]["license"])
        archives.append(str(archive_path))
    return archives


@pytest.fixture(scope="session")
def adcm_image_tags(cmd_opts) -> Tuple[str, str]:
    """Get tag parts of --adcm-image argument (split by ":")"""
    if not cmd_opts.adcm_image:
        pytest.fail("CLI parameter adcm_image should be provided")
    return tuple(parse_repository_tag(cmd_opts.adcm_image))  # type: ignore


# RBAC


@pytest.fixture()
@allure.title("Create test user")
def user(sdk_client_fs) -> User:
    """Create user for testing"""
    return sdk_client_fs.user_create(*TEST_USER_CREDENTIALS)


@pytest.fixture()
def user_sdk(user, adcm_fs) -> ADCMClient:
    """Returns ADCMClient object from adcm_client with testing user"""
    username, password = TEST_USER_CREDENTIALS
    return ADCMClient(url=adcm_fs.url, user=username, password=password)


# Websockets (Events)


@pytest.fixture()
async def adcm_ws(sdk_client_fs, adcm_fs) -> ADCMWebsocket:
    """
    Create a connection to ADCM websocket for Admin user
    and return ADCMWebsocket helper for tests.
    Should be used only in async environment.
    """
    addr = f"{adcm_fs.ip}:{adcm_fs.port}"
    async with websockets.client.connect(
        uri=f"ws://{addr}/ws/event/", subprotocols=["adcm", sdk_client_fs.api_token()]
    ) as conn:
        yield ADCMWebsocket(conn)


# ADCM DB


@pytest.fixture()
def adcm_db(launcher, adcm_fs: ADCM) -> QueryExecutioner | PostgreSQLQueryExecutioner:
    """Initialized QueryExecutioner for a function scoped ADCM"""
    if isinstance(launcher, ADCMWithPostgresLauncher):
        return PostgreSQLQueryExecutioner(launcher.postgres.container)

    return QueryExecutioner(adcm_fs.container)


# ADCM + LDAP

LDAP_PREFIX = "ldap://"
LDAPS_PREFIX = "ldaps://"


@allure.title("[SS] Get LDAP config")
@pytest.fixture(scope="session")
def ldap_config(cmd_opts) -> dict:
    """
    Load LDAP config from file as a dictionary.
    Returns empty dict if `--ldap-conf` is not presented.
    """
    if not cmd_opts.ldap_conf:
        return {}
    config_fp = pathlib.Path(cmd_opts.ldap_conf)
    if not config_fp.exists():
        raise ConfigError(f"Path to LDAP config file should exist: {config_fp}")
    with config_fp.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ConfigError('LDAP config file should have root type "dict"')
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    return config


@allure.title("[SS] Extract AD config")
@pytest.fixture(scope="session")
def ad_config(ldap_config: dict) -> LDAPTestConfig:
    """Create AD config from config file"""
    required_keys = {"uri", "admin_dn", "admin_pass", "base_ou_dn"}
    if "ad" not in ldap_config:
        raise ConfigError('To test LDAP with AD LDAP config file should have "ad" key')
    config = ldap_config["ad"]
    if not required_keys.issubset(config.keys()):
        raise ConfigError(
            'Not all required keys are presented in "ad" LDAP config.\n'
            f"Required: {required_keys}\n"
            f"Actual: {config.keys()}"
        )
    return LDAPTestConfig(
        config["uri"],
        config["admin_dn"],
        config["admin_pass"],
        config["base_ou_dn"],
        config.get("cert", None),
    )


@allure.title("Prepare LDAP entities manager")
@pytest.fixture()
def ldap_ad(request, ad_config) -> Generator[LDAPEntityManager, None, None]:
    """Create LDAP entities manager from AD config"""
    with LDAPEntityManager(ad_config, request.node.nodeid) as ldap_manager:
        yield ldap_manager


@allure.title("Create basic OUs for testing")
@pytest.fixture()
def ldap_basic_ous(ldap_ad):
    """Get LDAP group (ou) DNs for groups and users"""
    groups_ou_dn = ldap_ad.create_ou("groups-main")
    users_ou_dn = ldap_ad.create_ou("users-main")
    return groups_ou_dn, users_ou_dn


@allure.title("Create LDAP user without group")
@pytest.fixture()
def ldap_user(ldap_ad, ldap_basic_ous) -> dict:
    """Create LDAP AD user"""
    _, users_dn = ldap_basic_ous
    user = {"name": f"user_wo_group_{random_string(6)}", "password": random_string(12)}
    user["dn"] = ldap_ad.create_user(**user, custom_base_dn=users_dn)
    user_fields_to_modify = _create_extra_user_modlist(user)
    ldap_ad.update_user(user["dn"], **user_fields_to_modify)
    user.update(user_fields_to_modify)
    return user


@allure.title("Create LDAP group")
@pytest.fixture()
def ldap_group(ldap_ad, ldap_basic_ous) -> dict:
    """Create LDAP AD group for adding users"""
    group = {"name": "adcm_users"}
    groups_dn, _ = ldap_basic_ous
    group["dn"] = ldap_ad.create_group(**group, custom_base_dn=groups_dn)
    return group


@allure.title("Create LDAP user in group")
@pytest.fixture()
def ldap_user_in_group(ldap_ad, ldap_basic_ous, ldap_group) -> dict:
    """Create LDAP AD user and add it to a default "allowed to log to ADCM" group"""
    user = {"name": f"user_in_group_{random_string(6)}", "password": random_string(12)}
    _, users_dn = ldap_basic_ous
    user["dn"] = ldap_ad.create_user(**user, custom_base_dn=users_dn)
    user_fields_to_modify = _create_extra_user_modlist(user)
    ldap_ad.update_user(user["dn"], **user_fields_to_modify)
    user.update(user_fields_to_modify)
    ldap_ad.add_user_to_group(user["dn"], ldap_group["dn"])

    return user


@allure.title("Create one more LDAP group")
@pytest.fixture()
def another_ldap_group(ldap_ad, ldap_basic_ous) -> dict:
    """Create LDAP AD group for adding users"""
    group = {"name": "another_adcm_users"}
    groups_dn, _ = ldap_basic_ous
    group["dn"] = ldap_ad.create_group(**group, custom_base_dn=groups_dn)
    return group


@allure.title("Create LDAP user in non-default group")
@pytest.fixture()
def another_ldap_user_in_group(ldap_ad, ldap_basic_ous, another_ldap_group) -> dict:
    """Create LDAP AD user and add it to "another" ADCM in AD group"""
    _, users_dn = ldap_basic_ous
    user = {"name": f"a_user_in_group_{random_string(4)}", "password": random_string(12)}
    user_fields_to_modify = _create_extra_user_modlist(user)
    user["dn"] = ldap_ad.create_user(**user, custom_base_dn=users_dn)
    ldap_ad.update_user(user["dn"], **user_fields_to_modify)
    user.update(user_fields_to_modify)
    ldap_ad.add_user_to_group(user["dn"], another_ldap_group["dn"])

    return user


@pytest.fixture()
def ad_ssl_cert(adcm_fs, ad_config) -> Optional[pathlib.Path]:
    """Put SSL certificate from config to ADCM container and return path to it"""
    if ad_config.cert is None:
        return None
    path = pathlib.Path("/adcm/.ad-cert")
    result = adcm_fs.container.exec_run(["sh", "-c", f'echo "{ad_config.cert}" > {path}'])
    if result.exit_code != 0:
        raise ValueError("Failed to upload AD certificate to ADCM")
    return path


@allure.title("Configure ADCM for LDAP (AD) integration")
@pytest.fixture(params=[False], ids=["ssl_off"])
def configure_adcm_ldap_ad(request, sdk_client_fs: ADCMClient, ldap_basic_ous, ad_config, ad_ssl_cert):
    """Configure ADCM to allow AD users"""
    ssl_on = request.param
    groups_ou, users_ou = ldap_basic_ous

    configure_adcm_for_ldap(sdk_client_fs, ad_config, ssl_on, ad_ssl_cert, users_ou, groups_ou)


def _create_extra_user_modlist(user: dict) -> dict:
    return {
        "first_name": user["name"],
        "last_name": "Testovich",
        "email": f'{user["name"]}@nexistent.ru',
    }
