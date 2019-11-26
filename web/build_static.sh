#!/bin/sh -e
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

workdir=$(dirname "${0}")
cd "${workdir}/../"

# That is dirty!!!
# Due to fact that setting.py loaded during any manage.py operation
# we have to have all environment ready. But during run of colectstatic
# on CI we have no data/log and that force logger to fails.
# So we temporary make that dir to remove after operation.
mkdir -p data/log

python manage.py collectstatic --noinput

cp ./wwwroot/static/rest_framework/css/* ./wwwroot/static/rest_framework/docs/css/

# If there is something in it we could leave it.
rmdir ../data/log || true
