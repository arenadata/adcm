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

from typing import Any

import ruyaml
import ruyaml.comments


class FormatError(Exception):
    def __init__(self, path, message, data: Any = None, rule: Any = None, parent: Any = None, caused_by: Any = None):
        self.path = path
        self.message = message
        self.data = data
        self.rule = rule
        self.errors = caused_by
        self.parent = parent
        self.line = None
        if isinstance(data, ruyaml.comments.CommentedBase):
            self.line = data.lc.line
        elif parent and isinstance(parent, ruyaml.comments.CommentedBase):
            self.line = parent.lc.line
        super().__init__(message)


class SchemaError(Exception):
    pass


class DataError(Exception):
    pass
