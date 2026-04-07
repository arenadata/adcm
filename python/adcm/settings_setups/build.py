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

from application.di.providers.environment import EnvironmentProvider
from core.settings import Directories
import dishka

from .shared.base import *  # noqa
from .shared.constants import *  # noqa

container = dishka.make_container(EnvironmentProvider())
directories = container.get(Directories)
STATIC_ROOT = directories.base / "wwwroot/static/"
