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

from rest_framework.request import Request

from adcm import settings


def upload_file(request: Request) -> Path:
    file_data = request.data["file"]
    file_path = Path(settings.DOWNLOAD_DIR, file_data.name)
    with open(file_path, "wb+") as f:
        for chunk in file_data.chunks():
            f.write(chunk)
    return file_path
