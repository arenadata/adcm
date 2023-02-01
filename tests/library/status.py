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
Change status of Cluster, Service, Component and Host by imitating statuschecker behaviour
"""

import json
from typing import Collection, Tuple, Union

import requests
from adcm_client.objects import ADCMClient, Cluster, Component, Host
from adcm_pytest_plugin.docker.adcm import ADCM
from tests.library.utils import RequestFailedException, get_json_or_text

POSITIVE_STATUS = 0
DEFAULT_NEGATIVE_STATUS = 16
_PATH_TO_ADCM_SECRETS = '/adcm/data/var/secrets.json'

HostComponentTuple = Tuple[Host, Component]


class ADCMObjectStatusChanger:
    """
    Allows you to "change" status of dummy Components and Hosts.

    If you want to "enable" Cluster or Service,
        you should set positive status on all hosts and components on it.
    If you want to "disable" Cluster or Service,
        you should set negative status at least one of its components or hosts.

    After using status-changing methods you'll need to call `reread` method
        to be able to get newly set status.

    Consider that status != 16 will be reset to 16 after timeout (300 seconds).
    """

    def __init__(self, client: ADCMClient, container: ADCM):
        self.client = client
        api_root = client.url
        self.host_url_template = f"{api_root}/status/api/v1/host/" + "{}/"
        self.component_url_template = self.host_url_template + 'component/{}/'
        self._headers = {
            'Authorization': f'Token {self._extract_status_api_token(container)}',
            'Content-Type': 'application/json',
        }

    def enable_cluster(self, cluster: Cluster) -> None:
        """Enable cluster by setting positive status for each host and component"""
        hosts = set()
        for hostcomponent in cluster.hostcomponent():
            host_id, component_id = hostcomponent['host_id'], hostcomponent['component_id']
            self._set_component_status(host_id, component_id, POSITIVE_STATUS)
            if host_id not in hosts:
                self._set_host_status(host_id, POSITIVE_STATUS)
                hosts.add(host_id)

    def set_host_positive_status(self, host: Union[Host, Collection[Host]]) -> None:
        """Make host(s) "working" by setting status to 0"""
        if isinstance(host, Host):
            self._set_host_status(host.id, POSITIVE_STATUS)
        else:
            for host_to_change in host:
                self._set_host_status(host_to_change.id, POSITIVE_STATUS)

    def set_host_negative_status(
        self, host: Union[Host, Collection[Host]], status: int = DEFAULT_NEGATIVE_STATUS
    ) -> None:
        """Make host(s) "not working" by setting status != 0"""
        if isinstance(host, Host):
            self._set_host_status(host.id, status)
        else:
            for host_to_change in host:
                self._set_host_status(host_to_change.id, status)

    def set_component_positive_status(
        self, host_component: Union[HostComponentTuple, Collection[HostComponentTuple]]
    ) -> None:
        """Make component(s) "working" by setting status to 0"""
        if isinstance(host_component, tuple) and len(host_component) == 2:
            host, component = host_component
            self._set_component_status(host.id, component.id, POSITIVE_STATUS)
        else:
            for host, component in host_component:
                self._set_component_status(host.id, component.id, POSITIVE_STATUS)

    def set_component_negative_status(
        self,
        host_component: Union[HostComponentTuple, Collection[HostComponentTuple]],
        status: int = DEFAULT_NEGATIVE_STATUS,
    ) -> None:
        """Make component(s) "not working" by settings status != 0"""
        if isinstance(host_component, tuple) and len(host_component) == 2:
            host, component = host_component
            self._set_component_status(host.id, component.id, status)
        else:
            for host, component in host_component:
                self._set_component_status(host.id, component.id, status)

    def _set_host_status(self, host_id: int, status: int) -> None:
        """Set host status by id"""
        self._set_status(self.host_url_template.format(host_id), status)

    def _set_component_status(self, host_id: int, component_id: int, status: int) -> None:
        """Set status of component on host by ids"""
        self._set_status(self.component_url_template.format(host_id, component_id), status)

    def _set_status(self, url: str, status: int) -> None:
        """Set status for given URL (status have to be int)"""
        response = requests.post(
            url,
            headers=self._headers,
            json={'status': status},
        )
        if (status_code := response.status_code) >= 400:
            raise RequestFailedException(
                f'Request to ADCM status API failed with status "{status_code}" '
                f'and message: {get_json_or_text(response)}'
            )

    def _extract_status_api_token(self, adcm_container: ADCM) -> str:
        """Get status API token from secrets file"""
        exit_code, output = adcm_container.container.exec_run(f'cat {_PATH_TO_ADCM_SECRETS}')
        if exit_code != 0:
            raise ValueError(
                "Failed to extract token from ADCM secrets. "
                f"Container exec_run exit code - {exit_code}. Output: {output}."
            )
        return json.loads(output)['token']
