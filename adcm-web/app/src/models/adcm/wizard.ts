import type { JSONObject } from '@models/json';
import type { AdcmJob, AdcmSubJobDetails, AdcmSubJobLogItem } from '@models/adcm/jobs';
import type { AdcmConfiguration } from '@models/adcm/configuration';
import type { AdcmHostComponentMapRuleAction } from '@models/adcm/dynamicAction';

export type AdcmWizardMappingStepOperationType = 'add' | 'remove';
export type AdcmWizardProcessState = 'created' | 'completed' | 'broken';

export enum AdcmWizardStepStates {
  Created = 'created',
  Completed = 'completed',
  Running = 'running',
  Broken = 'broken',
}

export enum AdcmWizardMethodType {
  Submit = 'submit_step',
  Complete = 'complete',
  Reset = 'reset_step',
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
}

export interface AdcmActionProcessMappingStepRules {
  operation: AdcmHostComponentMapRuleAction;
  component: string;
  service: string;
}

interface DeltaItem {
  operation: AdcmWizardMappingStepOperationType;
  componentId: number;
  hostId: number;
}

export interface AdcmActionProcessMappingStep {
  id: number;
  displayName: string;
  name: string;
  type: AdcmWizardStepType.Mapping;
  state: AdcmWizardStepStates;
  rules: AdcmActionProcessMappingStepRules[];
  delta: DeltaItem[];
  cumulativeDelta: DeltaItem[];
}

export interface AdcmActionProcessLastStep {
  displayName: string;
  id: number;
  type: AdcmWizardStepType.LastStep;
  state: AdcmWizardStepStates;
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
  | AdcmWizardSubmitMappingStepPayload;

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
