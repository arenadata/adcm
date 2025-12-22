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

from functools import cache
import json

from cm.impl.config.repo import ConfigRepo
from cm.impl.config.validators import DefaultsVariantResolver, MainConfigVariantResolver
from cm.impl.job.repo import JobRepo
from cm.impl.wizard.repo import WizardRepo
from core.settings import Directories, Settings
import core
import yaml


@cache
def get_config_service():
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

    secrets_service = core.config.secrets.AnsibleSecrets(secret=secret)
    repo = ConfigRepo()

    validators = core.config.VariantValidators(main=MainConfigVariantResolver, default=DefaultsVariantResolver)
    # shouldn't work like that, but no other way for now
    settings_ = _get_settings()

    yspec_schema = yaml.safe_load((settings.CODE_DIR / "cm" / "yspec_schema.yaml").read_text())

    return core.config.ConfigService(
        repo=repo,
        secrets=secrets_service,
        directories=settings_.directories,
        variant_validators=validators,
        yspec_schema=yspec_schema,
    )


@cache
def get_job_service():
    repo = JobRepo()

    return core.job.JobService(repo=repo)


@cache
def get_wizard_service():
    settings_ = _get_settings()

    repo = WizardRepo()

    return core.action.wizard.WizardService(repo=repo, directories=settings_.directories)


def _get_settings() -> Settings:
    from django.conf import settings

    return Settings(
        directories=Directories(files=settings.FILE_DIR, bundles=settings.BUNDLE_DIR, downloads=settings.DOWNLOAD_DIR)
    )
