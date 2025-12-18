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

from functools import partial
from pathlib import Path
import json

from cm.impl.bundle.definition import definition_to_full_spec
from cm.impl.bundle.repo import BundleRepo
from cm.impl.config.repo import ConfigRepo
from cm.impl.config.validators import DefaultsVariantResolver, MainConfigVariantResolver
from core.settings import Directories
from dishka import Provider, Scope, provide
from use_cases.bundle import ParseBundleFromRequest
import core
import yaml


class FSProvider(Provider):
    scope = Scope.APP

    @provide
    def directories(self) -> Directories:
        from django.conf import settings

        return Directories(files=settings.FILE_DIR, bundles=settings.BUNDLE_DIR, downloads=settings.DOWNLOAD_DIR)


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def secrets(self) -> core.config.secrets.AnsibleSecrets:
        from django.conf import settings

        secret = settings.ANSIBLE_SECRET
        if not secret:
            if settings.SECRETS_FILE.is_file():
                # todo: temporal fallback to read secret from file,
                #       shouldn't be that way
                raw = settings.SECRETS_FILE.read_text()
                content = json.loads(raw)
                secret = content["adcmuser"]["password"]

            if not secret:
                message = "Ansible secret is undefined, work with secrets is impossible"
                raise ValueError(message)

        return core.config.secrets.AnsibleSecrets(secret=secret)

    @provide
    def yspec_schema(self) -> dict:
        from django.conf import settings

        schema_file: Path = settings.CODE_DIR / "cm" / "yspec_schema.yaml"
        schema_data = schema_file.read_text(encoding="utf-8")
        return yaml.safe_load(schema_data)

    @provide
    def validators(self) -> core.config.VariantValidators:
        return core.config.VariantValidators(main=MainConfigVariantResolver, default=DefaultsVariantResolver)

    repo = provide(ConfigRepo, provides=core.config.ConfigRepoI)
    service = provide(core.config.ConfigService)


class BundleProvider(Provider):
    scope = Scope.APP

    @provide
    def adcm_version(self) -> str:
        from django.conf import settings

        return settings.ADCM_VERSION

    @provide
    def parsers(self) -> list[tuple[core.bundle.parsing.VersionInfo, core.bundle.parsing.BundleParser]]:
        v_1_0 = (
            core.bundle.parsing.VersionInfo(tag="1.0", status="supported"),
            core.bundle.parsing.v_1_0.Parser(),
        )
        v_2_0 = (
            core.bundle.parsing.VersionInfo(tag="2.0", status="supported"),
            core.bundle.parsing.v_2_0.Parser(),
        )
        return [v_1_0, v_2_0]

    @provide
    def convert(self, secrets: core.config.secrets.AnsibleSecrets) -> core.bundle.ConvertConfigDefinition:
        return partial(definition_to_full_spec, secrets=secrets)

    repo = provide(BundleRepo, provides=core.bundle.BundleRepoI)
    service = provide(core.bundle.BundleService)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    parse_bundle_from_request = provide(ParseBundleFromRequest)
