"""ADSS fixtures"""
import time
from typing import Optional

import allure
import docker
import pytest
import requests

from docker.errors import NotFound
from _pytest.python import Function
from allure_commons.model2 import TestResult, Parameter
from allure_pytest.listener import AllureListener
from retry.api import retry_call  # pylint: disable=no-name-in-module
from adss_client.client import ADSSClient

from .steps.asserts import BodyAssertionError
from .steps.common import assume_step
from .utils.docker import (
    ADSS,
    DockerWrapper,
    get_initialized_adss_image,
    gather_adss_data_from_container,
    is_docker,
    ADSS_PROD_IMAGE,
)
from .utils.api_objects import ADSSApi
from .utils.tools import get_connection_ip, get_if_type


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):  # pylint: disable=unused-argument
    """
    There is no default info about test stages execution available in pytest
    This hook is meant to store such info in metadata
    """
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


def pytest_addoption(parser):
    """
    Additional options for ADSS testing
    """
    parser.addoption(
        "--disable-soft-assert",
        action="store_true",
        help="This option is needed to disable soft assert in 'flexible_assert_step' fixture",
    )
    parser.addoption("--staticimage", action="store", default=None)

    # Do not stop ADCM container after test execution
    # It is really useful for debugging
    parser.addoption("--dontstop", action="store_true", default=False)

    parser.addoption(
        "--adss-image-repo",
        action="store",
        default=None,
        help="ex: ci.arenadata.io/adss_core_dev or arenadata/adss_core"
        " then tag will be latest os ADSS_TAG environment value",
    )

    parser.addoption(
        "--adss-image-tag",
        action="store",
        default=None,
        help="ex: develop or latest, or ADSS-288",
    )
    parser.addoption("--nopull", action="store_true", default=False, help="don't pull image")
    parser.addoption(
        "--remote-executor-host",
        action="store",
        default=None,
        help="this option is used to initialise ADSS API with external IP "
        "to allow incoming connections from any remote executor (eg. Selenoid). "
        "Test will fail if remote host is unreachable",
    )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item: Function):
    """
    Pytest hook that overrides test parameters
    In case of adss tests, parameters in allure report don't make sense unlike test ID
    So, we remove all parameters in allure report but add one parameter with test ID
    """
    yield
    _override_allure_test_parameters(item)


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


@pytest.fixture(scope="session")
def cmd_opts(request):
    """Returns pytest request options object"""
    return request.config.option


# pylint: disable=redefined-outer-name
def _image(request, cmd_opts):
    """That fixture create ADSS container, waits until
    database becomes initialised and store that as images
    with random tag and name ci.arenadata.io/adssinit

    That can be useful to use that fixture to make ADSS
    container startup time shorter.

    Fixture returns list:
    repo, tag
    """

    pull = not cmd_opts.nopull
    dc = docker.from_env()
    params = dict()
    params["adss_repo"] = request.param

    # next step is to analise is it local debugging or common tests run
    if cmd_opts.staticimage:
        params["tag"] = cmd_opts.staticimage
    if cmd_opts.adss_image_repo:
        params["adss_repo"] = cmd_opts.adss_image_repo
    if cmd_opts.adss_image_tag:
        params["adss_tag"] = cmd_opts.adss_image_tag

    init_image = get_initialized_adss_image(pull=pull, dc=dc, **params)

    if not (cmd_opts.dontstop or cmd_opts.staticimage):

        def fin():
            image_name = "{}:{}".format(*init_image.values())
            for container in dc.containers.list(filters=dict(ancestor=image_name)):
                try:
                    container.wait(condition="removed", timeout=30)
                except ConnectionError:
                    # https://github.com/docker/docker-py/issues/1966 workaround
                    pass
            dc.images.remove(image_name, force=True)
            containers = dc.containers.list(filters=dict(ancestor=image_name))
            if len(containers) > 0:
                raise RuntimeWarning(f"There are containers left! {containers}")

        request.addfinalizer(fin)

    return init_image["repo"], init_image["tag"]


def _adss(image, cmd_opts, credentials, request, volumes=None, do_login=True) -> ADSS:
    repo, tag = image
    dw = DockerWrapper()
    ip = get_connection_ip(cmd_opts.remote_executor_host) if cmd_opts.remote_executor_host else None
    if ip and is_docker():
        if get_if_type(ip) == "0":
            raise EnvironmentError(
                "You are using network interface with 'bridge' "
                "type while running inside container."
                "There is no obvious way to get external ip in this case."
                "Try running container with pytest with --net=host option"
            )
    adss = dw.run_adss(
        image=repo,
        tag=tag,
        pull=False,
        ip=ip,
        labels={"pytest_node_id": request.node.nodeid},
        volumes=volumes,
    )

    def fin():
        if not request.config.option.dontstop:
            gather = True
            try:
                if not request.node.rep_call.failed:
                    gather = False
            except AttributeError:
                # There is no rep_call attribute. Presumably test setup failed,
                # or fixture scope is not function. Will collect /adcm/data anyway
                pass
            if gather:
                with allure.step(f"Gather /app/data/ from ADSS container: {adss.container.id}"):
                    file_name = f"{request.node.name}_{time.time()}"
                    try:
                        with gather_adss_data_from_container(adss) as data:
                            allure.attach(data, name="{}.tgz".format(file_name), extension="tgz")
                    except NotFound:
                        pass

            try:
                retry_call(
                    adss.container.kill,
                    exceptions=requests.exceptions.ConnectionError,
                    tries=5,
                    delay=5,
                )
            except NotFound:
                pass

    request.addfinalizer(fin)

    if do_login:
        adss.api.login(**credentials)

    return adss


@pytest.fixture(scope="session")
def adss_credentials():
    """
    Return username:password dict for API login
    """
    return {"username": "admin", "password": "admin"}


@pytest.fixture(scope="session", params=[ADSS_PROD_IMAGE], ids=["prod_adss"])
def image(request, cmd_opts):
    """
    Image fixture (session scope)
    """
    return _image(request, cmd_opts)


@pytest.fixture(params=[ADSS_PROD_IMAGE], ids=["prod_adss"])
def image_fs(request, cmd_opts):
    """
    Image fixture (function scope)
    """
    return _image(request, cmd_opts)


@pytest.fixture()
def adss_instance_factory(image_fs, cmd_opts, adss_credentials, request):
    """
    This factory creates independent ADSS instances (containers) from same image.
    Each object has a finalizer, so this is a safe way to create multiple instances.

    Example:
        def test_1(adss_instance_factory):
            first_adss_instance = adss_instance_factory()
            second_adss_instance = adss_instance_factory(volumes=SOME_DICT)
    """

    def _adss_instance_factory(volumes=None):
        step_title = (
            f"Start new ADSS instance with volumes: {volumes}"
            if volumes is not None
            else "Start new ADSS instance"
        )
        with allure.step(step_title):
            return _adss(image_fs, cmd_opts, adss_credentials, request, volumes)

    return _adss_instance_factory


@pytest.fixture()
def adss_fs(image, cmd_opts, adss_credentials, request) -> ADSSApi:
    """Runs ADSS container with previously initialized image.
    Returns authorized instance of ADSSApi object
    """
    return _adss(image, cmd_opts, adss_credentials, request).api


@pytest.fixture()
def adss_client_fs(image, cmd_opts, adss_credentials, request) -> ADSSClient:
    """
    Run ADSS and return ADSSClient object from adss_client
    """
    adss = _adss(image, cmd_opts, adss_credentials, request)
    client = ADSSClient(url=adss.url)
    client.auth(**adss_credentials)
    return client


@pytest.fixture()
def flexible_assert_step(cmd_opts):
    """
    Returns either allure.step or assume_step context manager
    depending on option '--disable-soft-assert'
    """

    def _flexible_assert_step(title, assertion_error=BodyAssertionError):
        if cmd_opts.disable_soft_assert is True:
            return allure.step(title)
        return assume_step(title, assertion_error)

    return _flexible_assert_step
