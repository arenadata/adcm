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
from typing import Iterable

from core import upgrade
from core.types import MainObjectDesc

from cm.impl.common.mappings import MAIN_CORE_TYPE_TO_MODEL


class UpgradeRepo(upgrade.UpgradeRepoI):
    def set_before_upgrade(self, targets: Iterable[MainObjectDesc], value: dict) -> None:
        grouped_by_type = defaultdict(list)

        for target in targets:
            grouped_by_type[target.type].append(target.id)

        for type_, ids in grouped_by_type.items():
            model = MAIN_CORE_TYPE_TO_MODEL[type_]
            model.objects.filter(id__in=ids).update(before_upgrade=value)
