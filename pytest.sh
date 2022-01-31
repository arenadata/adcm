#!/bin/sh
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


#pip3 install -U pip
pip3 install -r requirements-test.txt

find . -name "*.pyc" -type f -delete
find . -name "__pycache__" -type d -delete
{ # try
    pytest tests/api tests/functional tests/ui_tests -s -v -n auto --maxfail 30 \
    --showlocals --alluredir ./allure-results/ --durations=20 -p allure_pytest \
    --reruns 2 --remote-executor-host "$SELENOID_HOST" --timeout=1080 "$@" &&
    chmod -R o+xw allure-results
} || { # catch
    chmod -R o+xw allure-results
    exit 1
}
