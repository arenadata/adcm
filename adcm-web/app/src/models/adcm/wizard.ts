import type { JSONObject } from '@models/json';

export type AdcmWizardMappingStepOperationType = 'add' | 'remove';
export type AdcmWizardProcessState = 'created' | 'completed' | 'broken';

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
  state: string;
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
  state: string;
  configuration: AdcmWizardConfiguration;
}

export interface AdcmActionProcessMappingStep {
  id: number;
  processSyncKey: string;
  displayName: string;
  type: AdcmWizardStepType.Mapping;
  state: string;
  mapping: {
    rule: {
      operation: AdcmWizardMappingStepOperationType;
      componentId: number;
    }[];
    delta: {
      operation: AdcmWizardMappingStepOperationType;
      componentId: number;
      hostId: number;
    }[];
    suggetion: {
      operation: AdcmWizardMappingStepOperationType;
      hostId: number;
      componentId: number;
    }[];
  };
}

export interface AdcmActionProcessLastStep {
  displayName: string;
  id: number;
  type: AdcmWizardStepType.LastStep;
  state: string;
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

export interface AdcmWizardSubmitMappingStepPayload {
  method: AdcmWizardMethodType.Submit;
  params: {
    processSyncKey: string;
    stepId: number;
    hostComponentMapDelta: {
      add: {
        hostId: number;
        componentId: number;
      }[];
      remove: {
        hostId: number;
        componentId: number;
      }[];
    };
  };
}

export type AdcmWizardProcessOperationPayload =
  | AdcmWizardResetStepPayload
  | AdcmWizardSubmitOperationStepPayload
  | AdcmWizardSubmitConfigurationStepPayload
  | AdcmWizardCompleteOperationPayload
  | AdcmWizardSubmitMappingStepPayload;

export type AdcmWizardProcessOperation = AdcmActionWizardProcess;
