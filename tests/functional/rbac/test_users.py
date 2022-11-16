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

"""Test basic user-management scenarios"""

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied
from adcm_client.objects import ADCMClient, User
from adcm_client.wrappers.api import ADCMApiError, MethodNotAllowed
from coreapi.exceptions import ErrorMessage

# pylint: disable=redefined-outer-name

USERNAME = 'new_user'
PASSWORD = 'strongpassword'

HTTP_401_MESSAGE = '401 Unauthorized'

# !===== FIXTURES =====!


@pytest.fixture()
def new_user(sdk_client_fs: ADCMClient) -> User:
    """Create new user with default username and password"""
    return create_new_user(sdk_client_fs)


@pytest.fixture()
def new_user_client(new_user: User, sdk_client_fs: ADCMClient) -> ADCMClient:
    """Create client for user"""
    return ADCMClient(url=sdk_client_fs.url, user=new_user.username, password=PASSWORD)


# !===== TESTS =====!


def test_create_user(sdk_client_fs: ADCMClient):
    """Create new user and login under it"""
    create_new_user(sdk_client_fs)
    user_client = login_as_user(sdk_client_fs.url, USERNAME, PASSWORD)
    _check_basic_actions_are_available(user_client)


def test_delete_newly_created_user(new_user: User, sdk_client_fs: ADCMClient):
    """Create new user and delete it"""
    admin_client = sdk_client_fs
    new_user.delete()
    check_user_is_deactivated(admin_client, new_user.username)


def test_change_password(new_user: User, sdk_client_fs: ADCMClient):
    """Check password checks works as expected"""
    admin_client = sdk_client_fs
    adcm_url = sdk_client_fs.url
    new_client_password = USERNAME + '-hehe'
    new_password_from_admin = 'LAKJF02fj0kdjD)f'
    with allure.step("Login as user and change password own password"):
        user_client = login_as_user(adcm_url, USERNAME, PASSWORD)
        _check_basic_actions_are_available(user_client)
        user = _get_user_by_username(admin_client, new_user.username)
        user.change_password(new_client_password)
        _check_login_failed(adcm_url, USERNAME, PASSWORD)
        _check_client_is_unauthorized(user_client)
        user_client = login_as_user(adcm_url, USERNAME, new_client_password)
        _check_basic_actions_are_available(user_client)
    with allure.step("Change password as admin"):
        new_user.change_password(new_password_from_admin)
        _check_login_failed(adcm_url, USERNAME, new_client_password)
        _check_client_is_unauthorized(user_client)
        user_client = login_as_user(adcm_url, USERNAME, new_password_from_admin)
        _check_basic_actions_are_available(user_client)


def test_delete_built_in_user(sdk_client_fs: ADCMClient):
    """Test that deletion of built-in users is forbidden"""
    for built_in_user in sdk_client_fs.user_list(built_in=True):
        with allure.step(f'Try to delete built-in user {built_in_user}'):
            try:
                built_in_user.delete()
            except MethodNotAllowed:
                ...
            else:
                raise AssertionError(f'Built-in user {built_in_user.username} should not be allowed to be deleted')


# !===== STEPS =====!


@allure.step('Create user {username} with password {password} and check it is created')
def create_new_user(client: ADCMClient, username: str = USERNAME, password: str = PASSWORD) -> User:
    """Create new user, run checks that it's created"""
    new_user = client.user_create(username=username, password=password)
    assert (
        new_user.username == username
    ), f"Username of newly created user should be {username}, but it's {new_user.username}"
    check_user_exists(client, username)
    return new_user


@allure.step('Login as user {username} with password {password}')
def login_as_user(url: str, username: str, password: str) -> ADCMClient:
    """Login as given user into ADCM instance"""
    try:
        return ADCMClient(url=url, user=username, password=password)
    except ADCMApiError as e:
        raise AssertionError('Login failed') from e


@allure.step('Check that user {username} does exist')
def check_user_exists(client: ADCMClient, username: str):
    """Check that username is presented in list of users"""
    presented_usernames = {user.username for user in client.user_list()}
    assert username in presented_usernames, (
        f"User with username {username} should be in list of users, "
        f"but wasn't found among: {', '.join(presented_usernames)}."
    )


@allure.step('Check that user {username} is deactivated')
def check_user_is_deactivated(client: ADCMClient, username: str):
    """Check that username isn't presented in list of user"""
    presented_usernames = {user.username for user in client.user_list()}
    assert username in presented_usernames, f"User with username {username} should be in list of users"
    user: User = client.user(username=username)
    assert not user.is_active, "User should be inactive"


# !===== UTILITIES =====!


def _get_user_by_username(client: ADCMClient, username: str) -> User:
    """Get user by username"""
    user = client.user(username=username)
    if user is None:
        raise ValueError("User with name %s not found" % username)  # pylint: disable=consider-using-f-string
    return user


@allure.step('Check authorized client can get cluster list')
def _check_basic_actions_are_available(client: ADCMClient):
    """Check if basic actions are available for provided ADCM client"""
    try:
        client.cluster_list()
    except NoSuchEndpointOrAccessIsDenied as e:
        raise AssertionError('Call to get cluster list should be available for any user') from e


@allure.step('Check ADCM client has no access to ADCM')
def _check_client_is_unauthorized(client: ADCMClient):
    """Check that ADCM client can't perform basic actions, because session is out"""
    with pytest.raises(ErrorMessage) as e:
        client.cluster_list()
    assert (
        error_message := e.value.error.title
    ) == HTTP_401_MESSAGE, f'HTTP error should be {HTTP_401_MESSAGE}, not {error_message}'


@allure.step('Check login to ADCM fails with username {username} and password {password}')
def _check_login_failed(url: str, username: str, password: str) -> None:
    """Check that login to ADCM client fails with wrong credentials"""
    failed_auth_error_args = ('AUTH_ERROR', 'Wrong user or password')
    with pytest.raises(ADCMApiError) as e:
        ADCMClient(url=url, user=username, password=password)
    assert (
        e.value.args == failed_auth_error_args
    ), f'Expected error message is {e.value}, but {failed_auth_error_args} was expected'
