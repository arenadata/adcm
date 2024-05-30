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

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from time import sleep, time
from typing import Collection

from requests.exceptions import ConnectionError
from rest_framework.status import HTTP_201_CREATED, HTTP_405_METHOD_NOT_ALLOWED
import requests

from cm.collect_statistics.errors import RetriesExceededError, SenderConnectionError
from cm.collect_statistics.types import Sender


@dataclass(frozen=True, slots=True)
class SenderSettings:
    url: str
    adcm_uuid: str
    retries_limit: int
    retries_frequency: int
    request_timeout: float


class StatisticSender(Sender[Path]):
    __slots__ = ("settings",)

    def __init__(self, settings: SenderSettings):
        self.settings = settings

    def send(self, targets: Collection[Path]) -> None:
        if not targets:
            return

        self._check_connection()

        failed = deque()

        for try_number in range(self.settings.retries_limit):
            last_try_timestamp = time()

            for target in targets:
                if not self._send(target=target):
                    failed.append(target)

            if not failed:
                break

            targets, failed = failed, deque()

            if try_number < self.settings.retries_limit - 1:  # skip last iteration self._sleep() call
                self._sleep(timestamp=last_try_timestamp, frequency=self.settings.retries_frequency)

        else:
            raise RetriesExceededError(f"None of the {self.settings.retries_limit} attempts was successful")

    def _send(self, target: Path) -> bool:
        with target.open(mode="rb") as f:
            try:
                response = requests.post(
                    url=self.settings.url,
                    headers={"Adcm-UUID": self.settings.adcm_uuid, "accept": "application/json"},
                    files={"file": f},
                    timeout=self.settings.request_timeout,
                )
            except ConnectionError:
                return False

        return response.status_code == HTTP_201_CREATED

    def _check_connection(self) -> None:
        """Expecting 405 response on HEAD request without headers"""

        try:
            response = requests.head(url=self.settings.url, headers={}, timeout=self.settings.request_timeout)
        except ConnectionError as e:
            raise SenderConnectionError(f"Check connection: can't connect to {self.settings.url}") from e

        if response.status_code != HTTP_405_METHOD_NOT_ALLOWED:
            raise SenderConnectionError(
                f"Check connection: wrong return code for {self.settings.url}: {response.status_code}"
            )

    @staticmethod
    def _sleep(timestamp: float, frequency: int) -> None:
        sleep_seconds = timestamp + frequency - time()
        sleep_seconds = max(sleep_seconds, 0)

        sleep(sleep_seconds)
