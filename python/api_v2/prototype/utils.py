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
from cm.adcm_config.config import read_bundle_file
from cm.errors import raise_adcm_ex
from cm.models import Prototype


def check_obj(model, req):
    if isinstance(req, dict):
        kwargs = req
    else:
        kwargs = {"id": req}

    return model.obj.get(**kwargs)


def accept_license(proto: Prototype) -> None:
    if not proto.license_path:
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    if proto.license == "absent":
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    Prototype.objects.filter(license_hash=proto.license_hash, license="unaccepted").update(license="accepted")


def get_license_text(proto: Prototype) -> str | None:
    if not proto.license_path:
        return None

    if not isinstance(proto, Prototype):
        raise_adcm_ex("LICENSE_ERROR")

    return read_bundle_file(proto=proto, fname=proto.license_path, bundle_hash=proto.bundle.hash, ref="license file")
