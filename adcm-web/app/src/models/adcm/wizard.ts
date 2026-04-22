import type { JSONObject } from '@models/json';
import type { AdcmJob, AdcmSubJobDetails, AdcmSubJobLogItem } from '@models/adcm/jobs';
import type { AdcmConfiguration } from '@models/adcm/configuration';
import type { AdcmDynamicActionRunConfig, AdcmHostComponentMapRuleAction } from '@models/adcm/dynamicAction';

export type AdcmWizardMappingStepOperationType = 'add' | 'remove';
export type AdcmWizardProcessState = 'created' | 'completed' | 'broken';

export enum AdcmWizardStepStates {
  Created = 'created',
  Completed = 'completed',
  Running = 'running',
  Broken = 'broken',
  Skipped = 'skipped',
}

export enum AdcmWizardMethodType {
  Submit = 'submit_step',
  Complete = 'complete',
  Reset = 'reset_step',
  SkipStep = 'skip_step',
}

export enum AdcmWizardStepType {
  Operation = 'operation',
  Configuration = 'configuration',
  Mapping = 'mapping',
  LastStep = 'last_step',
}

export interface AdcmWizardStepConfigSchemaMetaData {
  isAdvanced?: boolean;
  isInvisible?: boolean;
  activation?: string;
  synchronization?: string;
  nullValue?: string;
  isSecret?: boolean;
  stringExtra?: string;
  enumExtra?: string;
}

export interface AdcmActionWizardProcess {
  id: number;
  state: AdcmWizardProcessState;
  stages: AdcmWizardStage[];
  currentStep: number;
  createdAt: string;
  syncKey: string;
}

export interface AdcmWizardStage {
  displayName: string;
  steps: AdcmActionProcessStep[];
  description: string;
}

export interface AdcmActionProcessOperationStep {
  id: number;
  processSyncKey: string;
  displayName: string;
  type: AdcmWizardStepType.Operation;
  uiOptions: {
    buttonName: string;
  };
  state: AdcmWizardStepStates;
  task: { id: number };
  description: string;
  required: boolean;
}

export interface AdcmWizardConfigSchema {
  $schema?: string;
  title?: string;
  description?: string;
  type?: unknown;
  properties?: Record<string, unknown>;
  readOnly?: boolean;
  required?: string[];
}

export interface AdcmWizardConfiguration {
  configSchema: AdcmWizardConfigSchema;
  adcmMeta: AdcmWizardStepConfigSchemaMetaData;
  config: JSONObject;
}

export interface AdcmActionProcessConfigurationStep {
  id: number;
  processSyncKey: string;
  displayName: string;
  type: AdcmWizardStepType.Configuration;
  state: AdcmWizardStepStates;
  configuration: AdcmWizardConfiguration;
  description: string;
  required: boolean;
}

export interface AdcmActionProcessMappingStepRules {
  operation: AdcmHostComponentMapRuleAction;
  component: string;
  service: string;
  description: string;
  required: boolean;
}

interface DeltaMapping {
  hostId: number;
  componentId: number;
}

export interface Delta {
  add: DeltaMapping[];
  remove: DeltaMapping[];
}

export interface AdcmActionProcessMappingStep {
  id: number;
  displayName: string;
  name: string;
  type: AdcmWizardStepType.Mapping;
  state: AdcmWizardStepStates;
  rules: AdcmActionProcessMappingStepRules[];
  delta: Delta | null;
  cumulativeDelta: Delta | null;
  description: string;
  required: boolean;
}

export interface AdcmActionProcessLastStep {
  displayName: string;
  id: number;
  type: AdcmWizardStepType.LastStep;
  state: AdcmWizardStepStates;
  description: string;
  required: boolean;
}

export type AdcmActionProcessStep =
  | AdcmActionProcessOperationStep
  | AdcmActionProcessConfigurationStep
  | AdcmActionProcessMappingStep
  | AdcmActionProcessLastStep;

export interface AdcmWizardResetStepPayload {
  method: AdcmWizardMethodType.Reset;
  params: {
    processSyncKey: string;
    stepId: number;
  };
}

export interface AdcmWizardSkipOperationStepPayload {
  method: AdcmWizardMethodType.SkipStep;
  params: {
    processSyncKey: string;
    stepId: number;
  };
}

export interface AdcmWizardSubmitOperationStepPayload {
  method: AdcmWizardMethodType.Submit;
  params: {
    processSyncKey: string;
    stepId: number;
  };
}

export interface AdcmWizardSubmitConfigurationStepPayload {
  method: AdcmWizardMethodType.Submit;
  params: {
    processSyncKey: string;
    stepId: number;
    configuration: Omit<AdcmWizardConfiguration, 'configSchema'>;
  };
}

export interface AdcmWizardCompleteOperationPayload {
  method: AdcmWizardMethodType.Complete;
  params: {
    processSyncKey: string;
  };
}

export interface AdcmWizardMapping {
  componentId: number;
  hostId: number;
}

export interface AdcmWizardMappingChangeHistory {
  add: AdcmWizardMapping[];
  remove: AdcmWizardMapping[];
}

export interface AdcmWizardSubmitMappingStepPayload {
  method: AdcmWizardMethodType.Submit;
  params: {
    processSyncKey: string;
    stepId: number;
    hostComponentMapDelta: AdcmWizardMappingChangeHistory;
  };
}

export type AdcmWizardProcessOperationPayload =
  | AdcmWizardResetStepPayload
  | AdcmWizardSubmitOperationStepPayload
  | AdcmWizardSubmitConfigurationStepPayload
  | AdcmWizardCompleteOperationPayload
  | AdcmWizardSubmitMappingStepPayload
  | AdcmWizardSkipOperationStepPayload;

export type AdcmWizardProcessOperation = AdcmActionWizardProcess;

export type AdcmWizardJobsData = Record<
  AdcmActionProcessStep['id'],
  {
    job?: AdcmJob;
    subJobLog?: Record<AdcmSubJobDetails['id'], AdcmSubJobLogItem[]>;
  }
>;

export interface ConfigurationMap {
  [stepId: number]: AdcmConfiguration | null;
}

export interface GetWizardProcessPayload {
  actionId: number;
  processId: number;
  actionHostGroupId: number;
}

export interface AdcmClusterGetProcessPayloadArgs extends GetWizardProcessPayload {
  clusterId: number;
}

export interface AdcmServiceGetProcessPayloadArgs extends GetWizardProcessPayload {
  clusterId: number;
  serviceId: number;
}

export interface AdcmComponentGetProcessPayloadArgs extends GetWizardProcessPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface GetWizardStepPayload {
  actionId: number;
  processId: number;
  stepId: number;
  actionHostGroupId: number;
}

export interface AdcmClusterGetStepPayloadArgs extends GetWizardStepPayload {
  clusterId: number;
}

export interface AdcmServiceGetStepPayloadArgs extends GetWizardStepPayload {
  clusterId: number;
  serviceId: number;
}

export interface AdcmComponentGetStepPayloadArgs extends GetWizardStepPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface CreateWizardProcessPayload {
  actionHostGroupId: number;
  actionId: number;
}

export interface AdcmClusterCreateProcessPayloadArgs extends CreateWizardProcessPayload {
  clusterId: number;
}

export interface AdcmServiceCreateProcessPayloadArgs extends CreateWizardProcessPayload {
  clusterId: number;
  serviceId: number;
}

export interface AdcmComponentCreateProcessPayloadArgs extends CreateWizardProcessPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface PostWizardOperationPayload {
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
  actionHostGroupId: number;
}

export interface AdcmClusterPostOperationPayloadArgs extends PostWizardOperationPayload {
  clusterId: number;
}

export interface AdcmServicePostOperationPayloadArgs extends PostWizardOperationPayload {
  clusterId: number;
  serviceId: number;
}

export interface AdcmComponentPostOperationPayloadArgs extends PostWizardOperationPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface RunDynamicActionPayload {
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
  actionHostGroupId: number;
}

export interface RunClusterDynamicActionPayload extends RunDynamicActionPayload {
  clusterId: number;
}

export interface RunServiceDynamicActionPayload extends RunDynamicActionPayload {
  clusterId: number;
  serviceId: number;
}

export interface RunComponentDynamicActionPayload extends RunDynamicActionPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}
