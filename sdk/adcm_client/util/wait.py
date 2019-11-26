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
import logging
import socket
from time import sleep
from time import time as now
from urllib.parse import urlparse

import urllib3

# pylint: disable=W0703


def wait_net_service(server, port, timeout, period=1):
    """ Wait for network service to appear
        @param timeout: in seconds, if None or 0 wait forever
        @return: True of False
    """

    start = now()

    s = socket.socket()
    while now() - start < timeout:
        try:
            s.connect((server, port))
        except Exception:
            pass

        else:
            s.close()
            return True
        sleep(period)
    return False


def wait_for_url(url, timeout, period=1):
    """ Wait for url to responce something with http 200
        @param timeout: in seconds
        @param period: in seconds
        @return: True if connect successfull, False if not
    """
    # Disable annoying warning:
    # connectionpool.py          662 WARNING  Retrying
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    urlparsed = urlparse(url)
    start = now()
    if not wait_net_service(urlparsed.hostname, urlparsed.port, timeout, period):
        return False

    http = urllib3.PoolManager()
    while now() - start < timeout:
        try:
            r = http.request('GET', url)
            if r.status == 200:
                return True
        except Exception:
            pass
        sleep(period)

    return False
