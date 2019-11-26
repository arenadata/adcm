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
import pytest


@pytest.fixture(scope="module")
def data():
    return [
        {
            "id": 1,
            "name": "ADB",
            "version": "5",
            "hash": "56daa2c4dccc2859ddd005ceed6b1f04a52a4a07",
            "description": "Arenadata Database",
            "date": "2018-08-20T13:24:37.649437Z",
            "url": "http://127.0.0.1:8000/api/v1/stack/bundle/1/",
            "update": "http://127.0.0.1:8000/api/v1/stack/bundle/1/update/"
        },
        {
            "id": 2,
            "name": "SSH Common",
            "version": "1.0",
            "hash": "f9f21250ebcadaaf9f1fd8a6b303e632d4159a75",
            "description": "",
            "date": "2018-08-20T13:25:19.090129Z",
            "url": "http://127.0.0.1:8000/api/v1/stack/bundle/2/",
            "update": "http://127.0.0.1:8000/api/v1/stack/bundle/2/update/"
        },
        {
            "id": 3,
            "name": "Digital Energy virtual machine",
            "version": "1.5",
            "hash": "865addbf0122f36a4de58aa58e0edb4a729528dc",
            "description": "",
            "date": "2018-08-20T13:26:35.018593Z",
            "url": "http://127.0.0.1:8000/api/v1/stack/bundle/3/",
            "update": "http://127.0.0.1:8000/api/v1/stack/bundle/3/update/"
        },
        {
            "id": 4,
            "name": "Monitoring",
            "version": "1.0",
            "hash": "2b64a9074dc7a869b433ecb40d4aeefc9d884800",
            "description": "Monitoring and Control Software",
            "date": "2018-08-20T13:26:41.564955Z",
            "url": "http://127.0.0.1:8000/api/v1/stack/bundle/4/",
            "update": "http://127.0.0.1:8000/api/v1/stack/bundle/4/update/"
        }
    ]
