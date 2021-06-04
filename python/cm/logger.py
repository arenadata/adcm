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
import os

import cm.config as config

log = logging.getLogger('adcm')
log.setLevel(logging.DEBUG)


def get_log_handler(fname):
    handler = logging.FileHandler(fname, 'a', 'utf-8')
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(module)s %(message)s", "%m-%d %H:%M:%S"
    )
    handler.setFormatter(fmt)
    return handler


log.addHandler(get_log_handler(config.LOG_FILE))

log_background_task = logging.getLogger('background_task')
log_background_task.setLevel(logging.INFO)
handler_background_task = logging.FileHandler(
    os.path.join(config.LOG_DIR, 'background_task.log'), 'a', 'utf-8'
)
handler_background_task.setLevel(logging.INFO)
fmt_background = logging.Formatter("%(asctime)s - %(message)s")
handler_background_task.setFormatter(fmt_background)
log_background_task.addHandler(handler_background_task)
