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

from dataclasses import dataclass
from typing import Literal

from core.bundle import BundleService
from core.cluster import ClusterRepoI, ExportData
from core.types import (
    ADCMCoreType,
    BindObjectDescriptor,
    ClusterBindSchema,
    ClusterHierarchyBeforeUpgradeBinds,
    Descriptor,
    ImportName,
    PrototypeImportSchema,
)
from core.versions import is_version_suitable


@dataclass(slots=True)
class BeforeUpgradeScenarios:
    cluster_repo: ClusterRepoI
    bundle_service: BundleService

    def restore_binds(
        self,
        cluster: Descriptor[Literal[ADCMCoreType.CLUSTER]],
        before_upgrade_binds: ClusterHierarchyBeforeUpgradeBinds,
        prototype_imports: dict[BindObjectDescriptor, dict[ImportName, PrototypeImportSchema]],
    ) -> None:
        """
        Restores binds of cluster and it's services.
        Skips binds with non-existent objects. Import rules violations can occur, recheck needed
        """

        sources: ExportData = self.cluster_repo.retrieve_export_data(
            clusters=before_upgrade_binds.source_cluster_ids,
            services=before_upgrade_binds.source_service_ids,
        )

        to_restore: list[ClusterBindSchema] = []

        for object_descriptor, binds in before_upgrade_binds.items():
            object_descriptor: BindObjectDescriptor
            binds: list[ClusterBindSchema]

            for bind in binds:
                if not (export := sources.retrieve_export_by_bind(bind)):
                    continue

                if not (target_import := prototype_imports.get(object_descriptor, {}).get(export.name, None)):
                    continue

                if is_version_suitable(version=export.version, versions_object=target_import):
                    to_restore.append(bind)

        self.cluster_repo.delete_hierarchy_binds(cluster_id=cluster.id)
        self.cluster_repo.create_binds(binds=to_restore, ignore_conflicts=True)
