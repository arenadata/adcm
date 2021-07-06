"""
ADSS auth token regeneration tests
"""
import contextlib
import os
import copy
import shutil
from http import HTTPStatus

import allure

from tests.test_data.generators import TestData
from tests.utils.api_objects import ExpectedResponse, Request
from tests.utils.docker import gather_adss_data_from_container
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods


pytestmark = [
    allure.suite("Token regeneration tests"),
    allure.link("https://arenadata.atlassian.net/browse/ADSS-282"),
]

positive_test_data = TestData(
    request=Request(method=Methods.LIST, endpoint=Endpoints.Cluster),
    response=ExpectedResponse(status_code=HTTPStatus.OK),
)
negative_test_data = copy.deepcopy(positive_test_data)
negative_test_data.response.status_code = HTTPStatus.UNAUTHORIZED


@contextlib.contextmanager
def _make_tmp_dir(path):
    """
    Make temp dir
    """

    if "CURDIR" in os.environ:  # This means tests are running in CI
        to_create_path = f"/app{path}"
        bind_path = f"{os.environ['CURDIR']}{path}"
    else:
        to_create_path = f"/tmp{path}"
        bind_path = copy.copy(to_create_path)

    shutil.rmtree(path, ignore_errors=True)  # Remove old dir if exist
    with allure.step(f"Create dir: {to_create_path}"):
        os.mkdir(to_create_path)  # Create directory on host or container that runs tests
    yield bind_path
    with allure.step(f"Remove dir: {to_create_path}"):
        shutil.rmtree(to_create_path)


def _exec_request(adss_instance, test_data):
    """
    Exec request to some ADSS instance
    """
    with allure.step(f"Exec request to ADSS instance: {adss_instance.container.id}"):
        adss_instance.api.exec_request(
            request=test_data.request, expected_response=test_data.response
        )


def _restart_container(adss_instance):
    """
    Restart some ADSS container by instance
    """
    with allure.step(f"Restart ADSS container: {adss_instance.container.id}"):
        adss_instance.restart()


def _stop_container(adss_instance):
    """
    Stop and remove some ADSS container by instance
    """
    container_id = adss_instance.container.id
    with allure.step(f"Stop and remove ADSS container: {container_id}"):
        with allure.step(f"Gather /app/data/ from ADSS container: {container_id}"):
            with gather_adss_data_from_container(adss_instance) as data:
                allure.attach(data, name="{}.tgz".format(container_id), extension="tgz")
        adss_instance.stop()


def test_after_restart(adss_instance_factory):
    """
    Test token regeneration after container restart
    """
    new_instance = adss_instance_factory()
    _exec_request(new_instance, positive_test_data)
    _restart_container(new_instance)
    _exec_request(new_instance, positive_test_data)


def test_after_restart_with_volumes(adss_instance_factory):
    """
    Test token regeneration after container restart with volumes
    """
    with _make_tmp_dir(path='/test_after_restart_with_volumes') as temp_volumes_dir:
        new_instance = adss_instance_factory(
            volumes={temp_volumes_dir: {'bind': '/app/data', 'mode': 'rw'}}
        )
        _exec_request(new_instance, positive_test_data)
        _restart_container(new_instance)
        _exec_request(new_instance, positive_test_data)


def test_new_installation(adss_instance_factory):
    """
    Test token regeneration after install new ADSS instance
    """
    first_instance = adss_instance_factory()
    old_api_token = first_instance.api.get_auth_token()
    _exec_request(first_instance, positive_test_data)
    _stop_container(first_instance)

    second_instance = adss_instance_factory()
    second_instance.api.set_auth_token(old_api_token)
    _exec_request(second_instance, negative_test_data)


def test_new_installation_with_volumes(adss_instance_factory):
    """
    Test token regeneration after install new ADSS instance with volumes
    """
    with _make_tmp_dir(path='/test_new_installation_with_volumes') as temp_volumes_dir:

        first_instance = adss_instance_factory(
            volumes={temp_volumes_dir: {'bind': '/app/data', 'mode': 'rw'}}
        )
        old_api_token = first_instance.api.get_auth_token()
        _exec_request(first_instance, positive_test_data)
        _stop_container(first_instance)

    with _make_tmp_dir(path='/test_new_installation_with_volumes') as temp_volumes_dir:
        second_instance = adss_instance_factory(
            volumes={temp_volumes_dir: {'bind': '/app/data', 'mode': 'rw'}}
        )
        second_instance.api.set_auth_token(old_api_token)
        _exec_request(second_instance, negative_test_data)


def test_upgrade_like(adss_instance_factory):
    """
    Test token regeneration after install new ADSS instance
    with volumes from first ADSS instance
    """
    with _make_tmp_dir(path='/test_upgrade_like') as temp_volumes_dir:

        first_instance = adss_instance_factory(
            volumes={temp_volumes_dir: {'bind': '/app/data', 'mode': 'rw'}}
        )
        old_api_token = first_instance.api.get_auth_token()
        _exec_request(first_instance, positive_test_data)
        _stop_container(first_instance)

        second_instance = adss_instance_factory(
            volumes={temp_volumes_dir: {'bind': '/app/data', 'mode': 'rw'}}
        )
        second_instance.api.set_auth_token(old_api_token)
        _exec_request(second_instance, positive_test_data)
