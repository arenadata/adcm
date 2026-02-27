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
import os

from adcm.feature_flags import use_new_job_scheduler
from cm.impl.bundle.definition import definition_to_full_spec
from cm.impl.bundle.repo import BundleRepo
from cm.impl.cluster.repo import ClusterRepo
from cm.impl.config.repo import ConfigRepo
from cm.impl.config.validators import DefaultsVariantResolver, MainConfigVariantResolver
from cm.impl.job.repo import JobRepo
from cm.impl.logs.repo import LogsRepo
from cm.impl.provider.repo import ProviderRepo
from cm.impl.scenarios.adcm import InitializeADCMLegacy, UpgradeADCMLegacy
from cm.impl.upgrade.repo import UpgradeRepo
from cm.impl.wizard.repo import WizardRepo
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService
from cm.legacy.services.bundle_alt.render import ActionArgs, ContextGatherer, TaskArgs
from cm.legacy.services.job.run import start_task
from core import secrets
from core.bundle import VersionSupportStatus
from core.dynamic_bundle.render import BundleRenderer
from core.dynamic_bundle.types import ContextGathererI
from core.files.local import LocalPathResolver
from core.scenarios.adcm import DefaultURL, InitializeADCM, UpgradeADCM
from core.settings import Directories
from dishka import Provider, Scope, provide, provide_all
from use_cases.bundle import InitOrUpgradeADCM, ParseBundleFromRequest
from use_cases.cluster.update import ResetBeforeUpgradeCluster
from use_cases.logs.check import AddCheckLogRecordForJob
from use_cases.provider.update import ResetBeforeUpgradeProvider
from use_cases.transition.cluster.create import CreateCluster, CreateServicesFromPrototypes
from use_cases.transition.cluster.delete import DeleteService, DeleteServiceFromAPI
from use_cases.transition.job.schedule import RetrieveConfigurationForAction, ScheduleTask, TaskStarter
import core
import yaml


class PathResolverProvider(Provider):
    scope = Scope.APP

    path_resolver = provide(LocalPathResolver)


class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def ansible_secrets(self, ansible_vault: secrets.AnsibleVault) -> core.config.secrets.AnsibleSecrets:
        return core.config.secrets.AnsibleSecrets(secret=ansible_vault)

    @provide
    def yspec_schema(self, directories: Directories) -> dict:
        # should be better typed and no so bound to code structure?
        schema_file: Path = directories.code / "cm" / "yspec_schema.yaml"
        schema_data = schema_file.read_text(encoding="utf-8")
        return yaml.safe_load(schema_data)

    @provide
    def validators(self) -> core.config.VariantValidators:
        return core.config.VariantValidators(main=MainConfigVariantResolver, default=DefaultsVariantResolver)

    repo = provide(ConfigRepo, provides=core.config.ConfigRepoI)
    service = provide(core.config.ConfigService)


class JobProvider(Provider):
    scope = Scope.APP

    repo = provide(JobRepo, provides=core.job.JobRepoI)
    service = provide(core.job.JobService)


class WizardProvider(Provider):
    scope = Scope.APP

    repo = provide(WizardRepo, provides=core.action.wizard.WizardRepoI)
    service = provide(core.action.wizard.WizardService)


class BundleProvider(Provider):
    scope = Scope.APP

    @provide
    def parsers(self) -> list[tuple[core.bundle.parsing.VersionInfo, core.bundle.parsing.BundleParser]]:
        v_1_0 = (
            core.bundle.parsing.VersionInfo(tag="1.0", status=VersionSupportStatus.SUPPORTED),
            core.bundle.parsing.v_1_0.Parser(),
        )
        v_2_0 = (
            core.bundle.parsing.VersionInfo(tag="2.0", status=VersionSupportStatus.SUPPORTED),
            core.bundle.parsing.v_2_0.Parser(),
        )
        return [v_1_0, v_2_0]

    @provide
    def convert(self, secrets: core.config.secrets.AnsibleSecrets) -> core.bundle.ConvertConfigDefinition:
        return partial(definition_to_full_spec, secrets=secrets)

    repo = provide(BundleRepo, provides=core.bundle.BundleRepoI)
    service = provide(core.bundle.BundleService)


class ClusterProvider(Provider):
    scope = Scope.APP

    repo = provide(ClusterRepo, provides=core.cluster.ClusterRepoI)
    service = provide(core.cluster.ClusterService)


class ProviderProvider(Provider):
    scope = Scope.APP

    repo = provide(ProviderRepo, provides=core.provider.ProviderRepoI)
    service = provide(core.provider.ProviderService)


class UpgradeProvider(Provider):
    scope = Scope.APP

    repo = provide(UpgradeRepo, provides=core.upgrade.UpgradeRepoI)
    service = provide(core.upgrade.UpgradeService)


class ActionHostGroupProvider(Provider):
    scope = Scope.APP

    repo = provide(ActionHostGroupRepo)
    service = provide(ActionHostGroupService)


class UtilsProvider(Provider):
    scope = Scope.APP

    context_gatherer = provide(ContextGatherer, provides=ContextGathererI[ActionArgs, TaskArgs])
    bundle_renderer = provide(BundleRenderer[ActionArgs, TaskArgs], provides=BundleRenderer[ActionArgs, TaskArgs])


class TaskStarterProvider(Provider):
    scope = Scope.APP

    @provide
    def task_starter(self) -> TaskStarter:
        if use_new_job_scheduler():
            return lambda _: None

        return start_task


class ScenariosProvider(Provider):
    scope = Scope.APP

    @provide
    def default_adcm_url(self) -> DefaultURL | None:
        adcm_url = os.getenv("DEFAULT_ADCM_URL")
        if adcm_url:
            return DefaultURL(adcm_url)

        return None

    initialize_adcm = provide(InitializeADCMLegacy, provides=InitializeADCM)
    upgrade_adcm = provide(UpgradeADCMLegacy, provides=UpgradeADCM)


class LogsServiceProvider(Provider):
    scope = Scope.APP

    repo = provide(LogsRepo, provides=core.logs.LogsRepoI)
    service = provide(core.logs.LogsService)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    parse_bundle_from_request = provide(ParseBundleFromRequest)
    init_upgrade_adcm = provide(InitOrUpgradeADCM, scope=Scope.APP)

    schedule_task = provide(ScheduleTask)

    retrieve_configuration_for_action = provide(RetrieveConfigurationForAction)

    create_cluster = provide(CreateCluster)

    add_services = provide(CreateServicesFromPrototypes)
    delete_service = provide(DeleteService)
    delete_service_from_api = provide(DeleteServiceFromAPI)

    upgrade = provide_all(
        ResetBeforeUpgradeCluster,
        ResetBeforeUpgradeProvider,
        # for now can't find out why is it failing in runner
        scope=Scope.APP,
    )

    add_check_log_record = provide(AddCheckLogRecordForJob)
