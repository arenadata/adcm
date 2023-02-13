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

import argparse
import os
import shutil
import sys
import tarfile

from check_adcm_config import check_config
from django.conf import settings

TMP_DIR = "/tmp/adcm_bundle_tmp"


def untar(bundle_file):
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)

    tar = tarfile.open(bundle_file)  # pylint: disable=consider-using-with
    tar.extractall(path=TMP_DIR)
    tar.close()


def get_config_files(path):
    conf_list = []
    conf_files = ("config.yaml", "config.yml")
    for root, _, files in os.walk(path):
        for conf_file in conf_files:
            if conf_file in files:
                conf_list.append(os.path.join(root, conf_file))
    return conf_list


def check_bundle(bundle_file, use_directory=False, verbose=False):
    if not use_directory:
        try:
            untar(bundle_file)
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)
    if verbose:
        print(f'Bundle "{bundle_file}"')
    for conf_file in get_config_files(TMP_DIR):
        check_config(conf_file, str(settings.CODE_DIR / "cm" / "adcm_schema.yaml"), verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check ADCM bundle file")
    parser.add_argument("bundle_file", type=str, help="ADCM bundle file name (bundle.tgz)")
    parser.add_argument("-d", "--dir", action="store_true", help="use bundle_file as bundle directory name")
    parser.add_argument("-v", "--verbose", action="store_true", help="print OK result")
    args = parser.parse_args()
    check_bundle(args.bundle_file, args.dir, args.verbose)
