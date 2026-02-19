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


from dishka import Provider

from application.di.providers.environment import EnvironmentProvider
from application.di.providers.main import (
    ActionHostGroupProvider,
    BundleProvider,
    ClusterProvider,
    ConfigProvider,
    JobProvider,
    PathResolverProvider,
    ProviderProvider,
    ScenariosProvider,
    TaskStarterProvider,
    UpgradeProvider,
    UseCaseProvider,
    UtilsProvider,
    WizardProvider,
)


def get_main_providers() -> tuple[Provider, ...]:
    return (
        ActionHostGroupProvider(),
        BundleProvider(),
        ClusterProvider(),
        ConfigProvider(),
        EnvironmentProvider(),
        JobProvider(),
        PathResolverProvider(),
        ProviderProvider(),
        ScenariosProvider(),
        TaskStarterProvider(),
        UpgradeProvider(),
        UseCaseProvider(),
        UtilsProvider(),
        WizardProvider(),
    )
