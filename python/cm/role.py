# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain a
# copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ruyaml

import cm.checker
from cm import config
from cm.logger import log
from cm.errors import raise_AdcmEx as err


def process(data):
    pass


def init_roles():
    try:
        with open(config.ROLE_FILE, encoding='utf_8') as fd:
            data = ruyaml.round_trip_load(fd)
    except FileNotFoundError:
        log.warning('Can not open role file "%s"', config.ROLE_FILE)
        return
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        err('INVALID_ROLE', f'YAML decode "{config.ROLE_FILE}" error: {e}')

    with open(config.ROLE_SCHEMA, encoding='utf_8') as fd:
        rules = ruyaml.round_trip_load(fd)

    try:
        cm.checker.check(data, rules)
    except cm.checker.FormatError as e:
        args = ''
        if e.errors:
            for ee in e.errors:
                if 'Input data for' in ee.message:
                    continue
                args += f'line {ee.line}: {ee}\n'
        err('INVALID_ROLE', f'"{config.ROLE_FILE}" line {e.line} error: {e}', args)
    process(data)
