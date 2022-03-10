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
Alternative settings for running ADCM with silk enabled
"""

from adcm.settings import *  # pylint: disable=wildcard-import, unused-wildcard-import

INSTALLED_APPS.append('silk')
MIDDLEWARE.insert(0, 'silk.middleware.SilkyMiddleware')
SILKY_PYTHON_PROFILER = True

ROOT_URLCONF = 'adcm.silk_urls'
