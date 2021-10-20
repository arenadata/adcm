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

"""Docker helper functions"""
from uuid import uuid4

import docker

from docker.models.containers import Container


def get_docker_client(remote_docker: str = None):
    """Get docker client based on is it remote or not"""
    if remote_docker is None:
        return docker.from_env(timeout=300)
    return docker.DockerClient(base_url=f"tcp://{remote_docker}", timeout=300)


def run_container(
    image,
    command: str = None,
    remote_docker: str = None,
    name: str = None,
    client: docker.DockerClient = None,
    **kwargs,
) -> Container:
    """
    Run container from the image with specify command
    """
    image, tag = image.split(":")
    client = client or get_docker_client(remote_docker)
    client.images.pull(image, tag)
    return client.containers.run(
        f"{image}:{tag}",
        tty=True,
        name=name or f'{image.rsplit("/")[-1]}_{uuid4().hex[:5]}',
        detach=True,
        remove=True,
        command=command,
        **kwargs,
    )
