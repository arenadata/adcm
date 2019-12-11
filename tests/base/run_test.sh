#!/bin/bash
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

port=8040

export DJANGO_SETTINGS_MODULE=tests.base.settings
export ADCM_STACK_DIR="tests/base"


init_db() {
    rm -f db_test.db
    ../../manage.py migrate
    ../../init_db.py 
    cp db_test.db fixture.db
}


run_debug() {
    rm -f db_test.db
    cp fixture.db db_test.db
    ../../manage.py runserver 8040
}


run_test() {
    rm -f db_test.db
    cp fixture.db db_test.db
    cd ../.. || exit 1
    ./server.sh start "${port}"
    echo "tests/base/test_api.py ${1} ${2}"
    TEST_CASE=""
    # shellcheck disable=SC2068
    for arg in $@; do
       if [[ "$arg" = '-d' ]]; then
          export BASE_DEBUG="True";
       else
          TEST_CASE="TestAPI.$arg"
       fi;
    done
    if [[ $TEST_CASE != '' ]]; then
    	./tests/base/test_api.py "$TEST_CASE"
    else
    	./tests/base/test_api.py
    fi;
    ./server.sh stop
}


if [[ ! -f fixture.db ]]; then
    init_db
fi

run_test "${1}" "${2}"
#run_debug
