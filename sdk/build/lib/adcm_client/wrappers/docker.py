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
import os
import random
import socket
import docker
from adcm_client.util.wait import wait_for_url
from adcm_client.wrappers.api import ADCMApiWrapper


MINDOCKERPORT = 8000
MAXDOCKERPORT = 9000

DEFAULTIP = '127.0.0.1'


class UnableToBind(Exception):
    pass


def _port_is_free(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((ip, port))
    if result == 0:
        return False
    return True


def _find_random_port(ip):
    for _ in range(0, 20):
        port = random.randint(MINDOCKERPORT, MAXDOCKERPORT)
        if _port_is_free(ip, port):
            return port
    raise UnableToBind("There is no free port for Docker after 20 tries.")


class ADCM():
    """
    Class that wraps ADCM Api operation over self.api (ADCMApiWrapper)
    and wraps docker over self.container (see docker module for info)
    """

    def __init__(self, container, ip, port):
        self.container = container
        self.ip = ip
        self.port = port
        self.url = 'http://{}:{}'.format(self.ip, self.port)
        self.api = ADCMApiWrapper(self.url)

    def stop(self):
        """Stops container"""
        self.container.stop()


class DockerWrapper():
    """Allow to connect to local docker daemon and spawn ADCM intances."""

    def __init__(self):
        self.client = docker.from_env()

    # pylint: disable=R0913
    def run_adcm(self, image='ci.arenadata.io/adcm',
                 remove=True, pull=True, name=None, tag=None, ip=DEFAULTIP, volumes=None):
        """
        Run ADCM in docker image.
        Return ADCM instance.

        Example:
        adcm = docker.run(image='ci.arenadata.io/adcm', tag=None, ip='127.0.0.1')

        If tag is None or is not present than it checks ADCM_TAG env
        variable and use it as image's tag. If there is no ADCM_TAG than
        it uses latest tag.
        """
        if tag is None:
            if "ADCM_TAG" in os.environ:
                tag = os.environ["ADCM_TAG"]
            else:
                tag = "latest"
        if pull:
            self.client.images.pull(image, tag)
        port = _find_random_port(ip)
        container = self.client.containers.run(
            "{}:{}".format(image, tag),
            ports={'8000': (ip, port)},
            volumes=volumes,
            remove=remove,
            detach=True,
            name=name
        )
        wait_for_url("http://{}:{}/api/v1/".format(ip, port), 60)
        return ADCM(container, ip, port)
