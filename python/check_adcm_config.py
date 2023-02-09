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
# pylint: disable=wrong-import-order

import argparse
import sys
from pathlib import Path

import cm.checker
import ruyaml
from django.conf import settings

import adcm.init_django  # pylint: disable=unused-import


def check_config(data_file, schema_file, print_ok=True):  # pylint: disable=too-many-return-statements
    rules = ruyaml.round_trip_load(open(schema_file, encoding=settings.ENCODING_UTF_8))
    try:
        data = ruyaml.round_trip_load(open(data_file, encoding=settings.ENCODING_UTF_8), version="1.1")
    except FileNotFoundError as e:
        print(e)

        return 1
    except ruyaml.constructor.DuplicateKeyError as e:
        print(f'Config file "{data_file}" Duplicate Keys Error:')
        print(f"{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}")

        return 1
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        print(f'Config file "{data_file}" YAML Parser Error:')
        print(f"{e}")

        return 1

    try:
        cm.checker.check(data, rules)
        if print_ok:
            print(f'Config file "{data_file}" is OK')

        return 0
    except cm.checker.DataError as e:
        print(f'File "{data_file}", error: {e}')

        return 1
    except cm.checker.SchemaError as e:
        print(f'File "{schema_file}" error: {e}')

        return 1
    except cm.checker.FormatError as e:
        print(f'Data File "{data_file}" Errors:')
        print(f"\tline {e.line}: {e.message}")
        if e.errors:
            for error in e.errors:
                if "Input data for" in error.message:
                    continue

                print(f"\tline {error.line}: {error.message}")

        print(f'Schema File "{schema_file}" line {rules[e.rule].lc.line}, Rule: "{e.rule}"')

        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check ADCM config file")
    parser.add_argument("config_file", type=str, help="ADCM config file name (config.yaml)")
    args = parser.parse_args()
    EXIT_CODE = check_config(args.config_file, Path(settings.CODE_DIR, "cm", "adcm_schema.yaml"))
    sys.exit(EXIT_CODE)
