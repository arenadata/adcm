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


class InvalidSpecKeyError(ValueError):
    """
    Raised when a string can't be a specification key.

    It's a `ValueError` descendant, because building a key out of unsuitable input
    is exactly that; domains are expected to convert it to their own error at their boundaries.
    """
