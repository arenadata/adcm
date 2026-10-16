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
Generic building blocks for hierarchical specifications.

A "specification" here is a flat mapping of `/`-separated keys to entries,
accompanied by a hierarchy that describes how those entries nest and how
entries of one level relate to each other.

Domains (configuration parameters, job scripts, ...) build their own
specifications on top of these primitives, supplying their own entry types
and their own notion of a level `rule`.

Package should be used via its public submodules (`keys`, `hierarchy`, `types`),
nothing is re-exported here on purpose.
"""
