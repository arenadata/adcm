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

from dishka import Container, Scope, make_container
from infra.di.providers import (
    BundleProvider,
    ConfigProvider,
    FeatureFlagProvider,
    FSProvider,
    JobProvider,
    UseCaseProvider,
    UtilsProvider,
    WizardProvider,
)


@cache
def prepare_container() -> Container:
    providers = (
        BundleProvider(),
        ConfigProvider(),
        JobProvider(),
        WizardProvider(),
        FSProvider(),
        UtilsProvider(),
        FeatureFlagProvider(),
        UseCaseProvider(),
    )

    return make_container(*providers)


class DishkaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.container = prepare_container()

    def __call__(self, request):
        with self.container(scope=Scope.REQUEST) as request_container:
            request.container = request_container
            return self.get_response(request)
