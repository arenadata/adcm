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

# pylint: disable=wrong-import-position,unused-import

import sys

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display   # pylint: disable=ungrouped-imports
    display = Display()

sys.path.append('/adcm')
import adcm.init_django
import cm.api
import cm.status_api
from cm.logger import log


DOCUMENTATION = """
    lookup: file
    author: Konstantin Voschanov <vka@arenadata.io>
    version_added: "0.1"
    short_description: create new host
    description:
        - This lookup create new host in ADCM DB
    options:
      _terms:
        description: fqdn, provider_id
        required: True
    notes:
"""

EXAMPLES = """
- debug: msg="add host id = {{lookup('adcm_add_host', 'myhost.com', provider.id) }}"

"""

RETURN = """
  _raw:
    description:
      - new host id
"""


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        log.debug('run %s %s', terms, kwargs)
        ret = []

        if len(terms) < 2:
            msg = 'not enough arguments to add host ({} of 2)'
            raise AnsibleError(msg.format(len(terms)))

        res = cm.api.add_provider_host(terms[1], terms[0])
        ret.append(res.id)
        return ret
