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

import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.environ.get('ADCM_BASE_DIR', BASE_DIR)

STACK_DIR = BASE_DIR
STACK_DIR = os.environ.get('ADCM_STACK_DIR', STACK_DIR)

LOG_DIR = os.path.join(BASE_DIR, 'data', 'log')
RUN_DIR = os.path.join(BASE_DIR, 'data', 'run')

BUNDLE_DIR = os.path.join(STACK_DIR, 'data', 'bundle')
DOWNLOAD_DIR = os.path.join(STACK_DIR, 'data', 'download')

FILE_DIR = os.path.join(STACK_DIR, 'data', 'file')

LOG_FILE = os.path.join(LOG_DIR, 'adcm.log')

SECRETS_FILE = os.path.join(BASE_DIR, 'data', 'var', 'secrets.json')

STATUS_SECRET_KEY = None

if os.path.exists(SECRETS_FILE):
    with open(SECRETS_FILE) as f:
        data = json.load(f)
        STATUS_SECRET_KEY = data['token']


class Job():
    CREATED = 'created'
    SUCCESS = 'success'
    FAILED = 'failed'
    RUNNING = 'running'
    LOCKED = 'locked'
    ABORTED = 'aborted'
