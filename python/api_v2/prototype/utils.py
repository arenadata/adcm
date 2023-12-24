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
from pathlib import Path

from cm.errors import AdcmEx
from cm.models import Prototype
from django.conf import settings


def accept_license(prototype: Prototype) -> None:
    if not prototype.license_path or prototype.license == "absent":
        raise AdcmEx(code="LICENSE_ERROR", msg="This bundle has no license")

    Prototype.objects.filter(license_hash=prototype.license_hash, license="unaccepted").update(license="accepted")


def get_license_text(license_path: str | None, path: str, bundle_hash: str) -> str | None:
    if license_path is None:
        return None

    if license_path.startswith("./"):
        path = Path(settings.BUNDLE_DIR, bundle_hash, path, license_path)
    else:
        path = Path(settings.BUNDLE_DIR, bundle_hash, license_path)

    try:
        return path.read_text(encoding=settings.ENCODING_UTF_8)
    except FileNotFoundError as error:
        raise AdcmEx(code="LICENSE_ERROR", msg=f'{bundle_hash} "{path}" is not found') from error
