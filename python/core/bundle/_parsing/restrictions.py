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

from collections.abc import Collection, Iterable

from adcm_version import compare_adcm_versions

from core.bundle._errors import BundleParsingError
from core.bundle._parsing.types import BundleParser, ParsingMeta, RootEntry, VersionInfo, VersionTag


def extract_parsing_meta(entries: Collection[RootEntry]) -> ParsingMeta:
    types_with_contract_version = {"cluster", "provider", "adcm"}
    meta = ParsingMeta()

    for entry in entries:
        if entry.data.get("type") in types_with_contract_version and (
            contract_version := entry.data.get("contract_version")
        ):
            meta.contract_version = contract_version

        # silenced SIM102 for better readability
        if adcm_min_version := entry.data.get("adcm_min_version"):  # noqa: SIM102
            if meta.adcm_min_version is None or compare_adcm_versions(adcm_min_version, meta.adcm_min_version) == 1:
                meta.adcm_min_version = adcm_min_version

    return meta


def pick_suitable_parser(version: VersionTag, parsers: Iterable[tuple[VersionInfo, BundleParser]]) -> BundleParser:
    for info, parser in parsers:
        if info.tag == version:
            return parser

    message = f"Bundle contract version {version} is not supported"
    raise BundleParsingError(message)


def check_adcm_min_version(current: str, required: str | None) -> None:
    if required is not None and compare_adcm_versions(required, current) > 0:
        raise BundleParsingError(
            f"This bundle required ADCM version equal to {required} or newer.",
        )
