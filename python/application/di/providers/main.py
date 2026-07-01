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

from audit.alt.core import NameHalfSplitter, NameSplitterSettings, build_name_splitter_settings_from_django_models
from cm.impl.adcm.repo import ADCMRepo
from cm.impl.bundle.definition import definition_to_full_spec
from cm.impl.bundle.repo import BundleRepo
from cm.impl.cluster.repo import ClusterRepo
from cm.impl.config.repo import ConfigRepo
from cm.impl.config.validators import DefaultsVariantResolver, MainConfigVariantResolver
from cm.impl.job.repo import JobClaimer, JobRepo
from cm.impl.logs.repo import LogsRepo
from cm.impl.metrics.repo import ClusterMetricsRepo
from cm.impl.provider.repo import ProviderRepo
from cm.impl.scenarios.adcm import InitializeADCMLegacy, UpgradeADCMLegacy
from cm.impl.scenarios.wizard import FillWizardStepSpecLegacy
from cm.impl.upgrade.repo import UpgradeRepo
from cm.impl.wizard.repo import WizardRepo
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService
from cm.legacy.services.bundle_alt.render import ActionArgs, ContextGatherer, TaskArgs
from cm.legacy.services.job.run import start_task
from cm.transition.action import RetrieveStartImpossibleReason
from cm.transition.status import StatusScenarios
from core import secrets
from core.action.job import (
    DirectOSTerminationSignaller,
    ExecutorTerminator,
    IndirectRepoTerminationSignaller,
    TaskRunnerTerminator,
    TerminationSignaller,
)
from core.dynamic_bundle.render import BundleRenderer
from core.dynamic_bundle.types import ContextGathererI
from core.files.local import LocalPathResolver
from core.scenarios.adcm import DefaultURL, InitializeADCM, UpgradeADCM
from core.scenarios.config import ConfigScenarios
from core.scenarios.wizard import FillWizardStepSpec
from core.settings import Directories
from dishka import Provider, Scope, provide, provide_all
from rbac.scenarios import RBACScenarios
from use_cases.bundle import AcceptLicense, InitOrUpgradeADCM, ParseBundleFromRequest
from use_cases.cluster.maintenance_mode import SetMaintenanceMode
from use_cases.cluster.update import ResetBeforeUpgradeCluster
from use_cases.logs.check import AddCheckLogRecordForJob
from use_cases.provider.update import ResetBeforeUpgradeProvider
from use_cases.transition.cluster.create import CreateCluster, CreateServicesFromPrototypes
from use_cases.transition.cluster.delete import DeleteService, DeleteServiceFromAPI
from use_cases.transition.config import (
    UpdateConfigurationFromJob,
    UpdateConfigurationOfHostGroup,
    UpdateConfigurationOfObject,
)
from use_cases.transition.config_revision import FindPrimaryConfigDiff, SetPrimaryConfigRevision
from use_cases.transition.hostprovider.create import CreateHostprovider
from use_cases.transition.job.schedule import (
    RetrieveConfigurationForAction,
    ScheduleMMChangingTask,
    ScheduleTask,
    TaskStarter,
)
from use_cases.transition.service_manage import ManageClusterServices
from use_cases.transition.upgrade import UpgradeObject
from use_cases.wizard import CompleteWizardOperationStep, InitiateWizardProcess, PerformWizardProcessOperation
import core
import yaml

from application.types import TaskRunnerMode


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

    repo = provide(JobRepo, provides=core.action.job.JobRepoI)
    service = provide(core.action.job.JobService)
    claimer = provide(JobClaimer, provides=core.action.scheduler.Claimer)

    task_runner_terminator = provide(TaskRunnerTerminator)
    executor_terminator = provide(ExecutorTerminator)

    @provide
    def termination_signaller(
        self,
        task_runner_mode: TaskRunnerMode,
        repo: core.action.job.JobRepoI,
        executor_terminator: ExecutorTerminator,
        task_runner_terminator: TaskRunnerTerminator,
    ) -> TerminationSignaller:
        match task_runner_mode:
            case TaskRunnerMode.SCHEDULLER:
                return IndirectRepoTerminationSignaller(repo)

            case TaskRunnerMode.INSTANT:
                return DirectOSTerminationSignaller(
                    task_runner_terminator=task_runner_terminator, executor_terminator=executor_terminator
                )

    @provide
    def task_starter(self, task_runner_mode: TaskRunnerMode) -> TaskStarter:
        match task_runner_mode:
            case TaskRunnerMode.SCHEDULLER:
                return lambda _: None

            case TaskRunnerMode.INSTANT:
                return start_task


class WizardProvider(Provider):
    scope = Scope.APP

    repo = provide(WizardRepo, provides=core.action.wizard.WizardRepoI)
    service = provide(core.action.wizard.WizardService)


class BundleProvider(Provider):
    scope = Scope.APP

    @provide
    def parsers(self) -> core.bundle.parsing.BundleParsers:
        v_2_1 = (
            core.bundle.VersionInfo(tag="2.1", status=core.bundle.ContractVersionStatus.SUPPORTED),
            core.bundle.parsing.v_2_1.Parser(),
        )
        return [v_2_1]

    @provide
    def available_contract_versions(
        self, parsers: core.bundle.parsing.BundleParsers
    ) -> core.bundle.AvailableContractVersions:
        return [cv_info for cv_info, _ in parsers]

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
    status_scenarios = provide(StatusScenarios)
    rbac_scenarios = provide(RBACScenarios)
    fill_wizard_step_spec = provide(
        FillWizardStepSpecLegacy,
        provides=FillWizardStepSpec[ActionArgs, TaskArgs],
    )
    retrieve_start_impossible_reason = provide(RetrieveStartImpossibleReason)
    config_scenarios = provide(ConfigScenarios)


class LogsServiceProvider(Provider):
    scope = Scope.APP

    repo = provide(LogsRepo, provides=core.logs.LogsRepoI)
    service = provide(core.logs.LogsService)


class MetricsProvider(Provider):
    scope = Scope.APP

    repo = provide(ClusterMetricsRepo, provides=core.metrics.ClusterMetricsRepoI)
    retrieve_cluster_metrics = provide(core.metrics.RetrieveClusterMetrics)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    parse_bundle_from_request = provide(ParseBundleFromRequest)
    init_upgrade_adcm = provide(InitOrUpgradeADCM, scope=Scope.APP)

    schedule_task = provide_all(ScheduleTask, ScheduleMMChangingTask)

    retrieve_configuration_for_action = provide(RetrieveConfigurationForAction)

    create_cluster = provide(CreateCluster)
    create_provider = provide(CreateHostprovider)

    # APP scope is required to inject these into `ExecutionTargetFactory` (`service_manage` internal script)
    add_services = provide(CreateServicesFromPrototypes, scope=Scope.APP)
    manage_cluster_services = provide(ManageClusterServices, scope=Scope.APP)
    delete_service = provide(DeleteService)
    delete_service_from_api = provide(DeleteServiceFromAPI)

    complete_wizard_operation_step = provide(CompleteWizardOperationStep, scope=Scope.APP)
    wizard = provide_all(
        InitiateWizardProcess,
        PerformWizardProcessOperation,
    )

    upgrade_object = provide(UpgradeObject)
    upgrade = provide_all(
        ResetBeforeUpgradeCluster,
        ResetBeforeUpgradeProvider,
        # for now can't find out why is it failing in runner
        scope=Scope.APP,
    )

    add_check_log_record = provide(AddCheckLogRecordForJob)

    set_maintenance_mode = provide(SetMaintenanceMode)

    update_configuration_of_object = provide(UpdateConfigurationOfObject)
    update_configuration_of_host_group = provide(UpdateConfigurationOfHostGroup)
    update_configuration_from_job = provide(UpdateConfigurationFromJob, scope=Scope.APP)
    set_primary_config_revision = provide(SetPrimaryConfigRevision)
    find_primary_config_diff = provide(FindPrimaryConfigDiff)

    accept_license = provide(AcceptLicense)


class AuditProvider(Provider):
    scope = Scope.APP

    @provide
    def name_splitter_settings(self) -> NameSplitterSettings:
        return build_name_splitter_settings_from_django_models()

    name_half_splitter = provide(NameHalfSplitter)


class ADCMProvider(Provider):
    scope = Scope.APP

    repo = provide(ADCMRepo, provides=core.adcm.ADCMRepoI)
