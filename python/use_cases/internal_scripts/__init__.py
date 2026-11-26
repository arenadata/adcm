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

"""
Internal scripts executed by the task runner for jobs of `internal` script type.

Internal scripts are entrypoint-like: each one validates what it's given by task/job
and then calls a use case or scenario. Because of that they may move "above" use cases
(e.g. to `jobs`) one day.
"""
