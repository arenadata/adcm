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

from collections import defaultdict

from core.types import HostID, HostName
from django.db.models import Value
from django.db.models.functions import Coalesce

from cm.models import Host
from cm.services.job.inventory import get_basic_info_for_hosts


def get_inventory() -> dict:
    """
    Collects inventory data for all existing hosts.
    Host groups are split by cluster edition (`ADCM` for unlinked hosts)
    """

    host_fqdn_edition: dict[HostID, tuple[HostName, str]] = {
        host["id"]: (host["fqdn"], host["edition"])
        for host in Host.objects.select_related("cluster__prototype__bundle")
        .values("id", "fqdn", edition=Coalesce("cluster__prototype__bundle__edition", Value("ADCM")))
        .all()
    }

    host_groups = defaultdict(lambda: defaultdict(dict))
    for host_id, info in get_basic_info_for_hosts(hosts=set(host_fqdn_edition.keys())).items():
        fqdn, edition = host_fqdn_edition[host_id]
        host_groups[edition]["hosts"][fqdn] = info.dict(by_alias=True, exclude_defaults=True)

    return {"all": {"children": host_groups}}
