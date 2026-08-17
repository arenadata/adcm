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

from typing import Literal, TypedDict

from cm.models import Bundle, ObjectType, Prototype


class BundlePrototypeRow(TypedDict):
    contract_version: str
    name: str
    display_name: str
    version: str
    obj_type: Literal[ObjectType.CLUSTER, ObjectType.PROVIDER]


def create_bundle_and_prototype_rows(
    rows: list[BundlePrototypeRow],
) -> list[tuple[Bundle, Prototype]]:
    bundles = Bundle.objects.bulk_create(
        [
            Bundle(
                name=row["name"],
                version=row["version"],
                hash="hash",
                contract_version=row["contract_version"],
            )
            for row in rows
        ]
    )
    prototypes = Prototype.objects.bulk_create(
        [
            Prototype(
                bundle=bundle,
                type=row["obj_type"],
                name=row["name"],
                display_name=row["display_name"],
                version=row["version"],
            )
            for bundle, row in zip(bundles, rows, strict=True)
        ]
    )

    return list(zip(bundles, prototypes, strict=True))
