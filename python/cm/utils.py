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

from operator import attrgetter


def filter_by_attribute(objects, attr_path, value, op, default=None):
    """
    Filters <objects> iterable by applying operator <op> on
    object's (nested) attribute in <attr_path> with <value>.
    If <default> is not None, yields it instead of unsuitable object

    Args:
        objects: iterable of objects
        attr_path: dotted target attribute path
        value: target value to compare with
        op: operator, performing comparison (func of two arguments)
        default: if specified, yields <default> instead of unsuitable object
    Returns:
        generator
    """
    get = attrgetter(attr_path)
    for obj in objects:
        if op(get(obj), value):
            yield obj
        else:
            if default is not None:
                yield default
