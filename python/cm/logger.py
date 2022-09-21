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

from cm import config

logger = logging.getLogger('adcm')
logger.setLevel(logging.DEBUG)


def get_log_handler(fname):
    handler = logging.FileHandler(fname, 'a', 'utf-8')
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(module)s %(message)s", "%m-%d %H:%M:%S"
    )
    handler.setFormatter(fmt)
    return handler


logger.addHandler(get_log_handler(config.LOG_FILE))
