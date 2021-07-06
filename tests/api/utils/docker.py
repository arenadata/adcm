"""Module helps to run ADSS in docker"""
import io
import os
import random
import re
import socket
from contextlib import contextmanager
from gzip import compress

import allure
import docker
from docker.errors import APIError, ImageNotFound

from .api_objects import ADSSApi
from .tools import wait_for_url, random_string

MIN_DOCKER_PORT = 8000
MAX_DOCKER_PORT = 9000
DEFAULT_IP = "127.0.0.1"
CONTAINER_START_RETRY_COUNT = 20
ADSS_PROD_IMAGE = "ci.arenadata.io/adss_core"
ADSS_DEV_IMAGE = "ci.arenadata.io/adss_core_dev"


class UnableToBind(Exception):
    """Raise when it is impossible to get a free port"""


class RetryCountExceeded(Exception):
    """Raise when container was not started"""


def _port_is_free(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((ip, port))
    if result == 0:
        return False
    return True


def _find_random_port(ip):
    for _ in range(0, 20):
        port = random.randint(MIN_DOCKER_PORT, MAX_DOCKER_PORT)
        if _port_is_free(ip, port):
            return port
    raise UnableToBind("There is no free port for Docker after 20 tries.")


def is_docker():
    """
    Look into cgroup to detect if we are in container
    """
    path = "/proc/self/cgroup"
    try:
        with open(path) as cgroup:
            for line in cgroup:
                if re.match(r"\d+:[\w=]+:/docker(-[ce]e)?/\w+", line):
                    return True
    except FileNotFoundError:
        pass
    return False


class ADSS:  # pylint: disable=too-few-public-methods
    """
    Class that wraps ADSS Api operation over self.api
    and wraps docker over self.container (see docker module for info)
    """

    def __init__(self, container, ip, port):
        self.container = container
        self.ip = ip
        self.port = port
        self.url = 'http://{}:{}'.format(self.ip, self.port)
        self.api = ADSSApi(self.url)

    def stop(self):
        """Stops container"""
        self.container.stop()

    def restart(self):
        """Restart container"""
        self.container.restart()
        if is_docker():
            auth_token = self.api.get_auth_token()
            self.ip = DockerWrapper().client.api.inspect_container(self.container.id)[
                'NetworkSettings'
            ]['IPAddress']
            self.url = 'http://{}:{}'.format(self.ip, self.port)
            self.api = ADSSApi(self.url)
            self.api.set_auth_token(auth_token)
        wait_for_url(self.url, 60)


class DockerWrapper:
    """Allow to connect to local docker daemon and spawn ADSS instances."""

    __slots__ = ("client",)

    def __init__(self):
        self.client = docker.from_env()

    # pylint: disable=too-many-arguments
    def run_adss(
        self,
        image=None,
        labels=None,
        remove=True,
        pull=True,
        name=None,
        tag=None,
        ip=None,
        volumes=None,
    ):
        """
        Run ADSS in docker image.
        Return ADSS instance.

        Example:
        adss = docker.run(image='ci.arenadata.io/adss', tag=None, ip='127.0.0.1')

        If tag is None or is not present than it checks ADCM_TAG env
        variable and use it as image's tag. If there is no ADCM_TAG than
        it uses latest tag.
        """
        if image is None:
            image = ADSS_PROD_IMAGE
        if tag is None:
            tag = os.environ.get("APP_TAG", "master")
        if pull:
            self.client.images.pull(image, tag)
        if os.environ.get("BUILD_TAG"):
            if not labels:
                labels = {}
            labels.update({"jenkins-job": os.environ["BUILD_TAG"]})
        if not ip:
            ip = DEFAULT_IP

        container, port = self.adss_container(
            image=image, labels=labels, remove=remove, name=name, tag=tag, ip=ip, volumes=volumes
        )

        # If test runner is running in docker than 127.0.0.1
        # will be local container loop interface instead of host loop interface
        # so we need to establish ADCM API connection using internal docker network
        if ip == DEFAULT_IP and is_docker():
            container_ip = self.client.api.inspect_container(container.id)['NetworkSettings'][
                'IPAddress'
            ]
            port = '8000'
        else:
            container_ip = ip

        wait_for_url("http://{}:{}/api/v1/".format(container_ip, port), 60)
        return ADSS(container, container_ip, port)

    # pylint: disable=too-many-arguments
    def adss_container(
        self, image=None, labels=None, remove=True, name=None, tag=None, ip=None, volumes=None
    ):
        """
        Run ADCM in docker image.
        Return ADCM container and bind port.
        """
        for _ in range(0, CONTAINER_START_RETRY_COUNT):
            port = _find_random_port(ip)
            try:
                with allure.step(f"Run container: {image}:{tag}"):
                    container = self.client.containers.run(
                        "{}:{}".format(image, tag),
                        ports={'8000': (ip, port)},
                        volumes=volumes,
                        remove=remove,
                        detach=True,
                        labels=labels,
                        name=name,
                    )
                break
            except APIError as err:
                if (
                    'failed: port is already allocated' in err.explanation
                    or 'bind: address already in use' in err.explanation  # noqa: W503
                ):
                    # such error excepting leaves created container and there is
                    # no way to clean it other than from docker library
                    pass
                else:
                    raise err
        else:
            raise RetryCountExceeded(
                f"Unable to start container after {CONTAINER_START_RETRY_COUNT} retries"
            )
        return container, port


@contextmanager
def gather_adss_data_from_container(adss):
    """Get archived data from ADSS container and return it compressed"""
    bits, _ = adss.container.get_archive('/app/data/')

    with io.BytesIO() as stream:
        for chunk in bits:
            stream.write(chunk)
        stream.seek(0)
        yield compress(stream.getvalue())


def get_initialized_adss_image(
    repo="ci.arenadata.io/adss_coreinit",
    tag=None,
    adss_repo=None,
    adss_tag=None,
    pull=True,
    dc=None,
) -> dict:
    """
    We consider that if we know tag, staticimage option is used,
    container is already initialized. In case if option is used but image is absent
    we create image with such tag for further use.
    If we don't know tag image must be initialized, tag will be randomly generated.
    """
    if not dc:
        dc = docker.from_env()

    if tag and image_exists(repo, tag, dc):  # pylint: disable=no-else-return
        return {'repo': repo, 'tag': tag}
    else:
        if not tag:
            tag = random_string()
        return init_adss(repo, tag, adss_repo, adss_tag, pull)


def init_adss(repo, tag, adss_repo, adss_tag, pull):
    """Run adss and commit container as a new image"""
    dw = DockerWrapper()
    adss = dw.run_adss(image=adss_repo, tag=adss_tag, remove=False, pull=pull)
    # Do initialized container snapshot a snapshot
    adss.container.stop()
    adss.container.commit(repository=repo, tag=tag)
    adss.container.remove()
    return {'repo': repo, 'tag': tag}


def image_exists(repo, tag, dc=None):
    """Check that image with repo and tag exists"""
    if dc is None:
        dc = docker.from_env()
    try:
        dc.images.get(name='{}:{}'.format(repo, tag))
    except ImageNotFound:
        return False
    return True
