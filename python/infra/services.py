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
import importlib

import core
import dishka

# this stuff is deprecated, don't  use it in new code


@cache
def prepare_container():
    # dynamic for testing purposes, very tricky, NEVER reuse
    from django.conf import settings

    module_name, func_name = settings.DEFAULT_DISHKA_PROVIDERS.rsplit(".", maxsplit=1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    providers = func()

    return dishka.make_container(*providers)


def get_config_service():
    return prepare_container().get(core.config.ConfigService)


def get_wizard_service():
    return prepare_container().get(core.action.wizard.WizardService)
