#!/usr/bin/env python3
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
import ruyaml
import argparse

import cm.config
import cm.checker


def check_config(data_file, schema_file):
    rules = ruyaml.round_trip_load(open(schema_file))
    try:
        data = ruyaml.round_trip_load(open(data_file), version="1.1")
    except ruyaml.constructor.DuplicateKeyError as e:
        print(f'Config file "{data_file}" Duplicate Keys Error:\n{str(e)}')
        return

    try:
        cm.checker.check(data, rules)
        print(f'Config file "{data_file}" is OK')
    except cm.checker.DataError as e:
        print(f'File "{data_file}", error: {e}')
    except cm.checker.SchemaError as e:
        print(f'File "{schema_file}" error: {e}')
    except cm.checker.FormatError as e:
        print(f'Data File "{data_file}" Errors:')
        print(f'\tline {e.line}: {e.message}')
        if e.errors:
            for ee in e.errors:
                if 'Input data for' in ee.message:
                    continue
                print(f'\tline {ee.line}: {ee.message}')
        print(f'Schema File "{schema_file}" line {rules[e.rule].lc.line}, Rule: "{e.rule}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check ADCM config file')
    parser.add_argument("config_file", type=str, help="ADCM config file name (config.yaml)")
    args = parser.parse_args()
    check_config(args.config_file, os.path.join(cm.config.CODE_DIR, 'cm', 'adcm_schema.yaml'))
