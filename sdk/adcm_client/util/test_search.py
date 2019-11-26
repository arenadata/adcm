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
from .search import search, search_one, TooManyResult


def test_search_one_too_many_result(data):
    with pytest.raises(TooManyResult):
        result = search_one(data)
        assert result is None


def test_search_one_not_found(data):
    result = search_one(data, name='azaza')
    assert result is None


def test_search_one(data):
    result = search_one(data, id=1)
    assert result['name'] == 'ADB'


def test_search_found(data):
    result = list(search(data))
    assert len(result) == 4
    result = list(search(data, version="1.0"))
    assert len(result) == 2
    assert result[0]['id'] == 2 or result[1]['id'] == 2


def test_search_generator(data):
    for i in search(data):
        assert "date" in i


def test_search_not_found(data):
    # pylint: disable=unused-variable
    for i in search(data, description=1):
        assert False  # We just should not be there
    assert True
