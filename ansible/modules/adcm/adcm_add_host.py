#!/usr/bin/python
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

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_add_host
short_description: create new host
description:
    - The C(adcm_add_host) module create new host in ADCM DB
options:
  provider:
    description:
      - ADCM host provider id
    required: yes
    type: int
  fqdn:
    description:
      - Host FQDN
    required: yes
'''

EXAMPLES = r'''
- name: add host
  adcm_add_host:
    provider: "{{provider.id}}"
    fqdn: my.host.com
'''

RETURN = r'''
result:
  host: id of new created host
'''

import sys

from ansible.module_utils.basic import AnsibleModule

sys.path.append('/adcm')
import adcm.init_django
import cm.api
import cm.status_api
from cm.errors import AdcmEx
from cm.logger import log


def main():
    module = AnsibleModule(argument_spec={
        'provider': {'type': 'int', 'required': True},
        'fqdn': {'type': 'str', 'required': True},
    })

    provider_id = module.params['provider']
    fqdn = module.params['fqdn']

    log.debug('ansible adcm_add_host: %s, %s', provider_id, fqdn)
    try:
        host = cm.api.add_provider_host(provider_id, fqdn)
    except AdcmEx as e:
        module.fail_json(code=e.code, msg=e.msg)
    module.exit_json(host=host.id)


if __name__ == '__main__':
    main()
