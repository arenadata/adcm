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
    ADCMProvider,
    AuditProvider,
    BundleProvider,
    ClusterProvider,
    ConcernProvider,
    ConfigProvider,
    JobProvider,
    LogsServiceProvider,
    MetricsProvider,
    PathResolverProvider,
    ProviderProvider,
    ScenariosProvider,
    UpgradeProvider,
    UseCaseProvider,
    UtilsProvider,
    WizardProvider,
)
from application.di.providers.task_runner import JobUseCaseProvider, TaskRunnerProvider


def get_ansible_plugin_providers() -> tuple[Provider, ...]:
    return (
        BundleProvider(),
        LogsServiceProvider(),
        ClusterProvider(),
        ConcernProvider(),
        ConfigProvider(),
        EnvironmentProvider(),
        JobProvider(),
        PathResolverProvider(),
        ProviderProvider(),
        ScenariosProvider(),
        UpgradeProvider(),
        UseCaseProvider(),
        UtilsProvider(),
        WizardProvider(),
    )


def get_task_runner_providers() -> tuple[Provider, ...]:
    return *get_ansible_plugin_providers(), TaskRunnerProvider(), AuditProvider()


def get_main_providers() -> tuple[Provider, ...]:
    from application.di.providers.celery import CeleryProvider

    providers = (
        ActionHostGroupProvider(),
        CeleryProvider(),
        MetricsProvider(),
        JobUseCaseProvider(),
        ADCMProvider(),
    )

    return *get_task_runner_providers(), *providers
