import type { RequestOptions } from '@api/httpClient/HttpClient';
import type {
  AdcmActionProcessStep,
  AdcmActionWizardProcess,
  AdcmWizardProcessOperation,
  AdcmWizardProcessOperationPayload,
  CreateWizardProcessPayload,
  GetWizardProcessPayload,
  GetWizardStepPayload,
  PostWizardOperationPayload,
  RunDynamicActionPayload,
} from '@models/adcm/wizard';

export type WizardOwner = 'cluster' | 'service' | 'component';
export type WizardOwnerId = 'clusterId' | 'serviceId' | 'componentId';

interface ClusterArgs {
  clusterId: number;
}

interface ServiceArgs {
  clusterId: number;
  serviceId: number;
}

interface ComponentArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

interface WizardOwnerArgsMap {
  cluster: ClusterArgs;
  service: ServiceArgs;
  component: ComponentArgs;
}

export type EntityArgs<T extends WizardOwner> = WizardOwnerArgsMap[T];

export type SomeEntityArgs = WizardOwnerArgsMap[WizardOwner];

export interface AdcmGetProcessPayload {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  actionId: number;
  processId: number;
  actionHostGroupId: number;
}

export interface AdcmGetStepPayload {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  actionId: number;
  processId: number;
  stepId: number;
  actionHostGroupId: number;
}

export interface AdcmGetStepsPayload extends Omit<AdcmGetStepPayload, 'stepId'> {
  stepIds: number[];
}

export interface AdcmCreateProcessPayload {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  actionId: number;
  actionHostGroupId: number;
}

export interface AdcmPostOperationPayload {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  actionId: number;
  processId: number;
  operation: AdcmWizardProcessOperationPayload;
  actionHostGroupId: number;
}

export interface RunDynamicActionArgs extends RunDynamicActionPayload {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
}

export interface AdcmPostTaskOperationPayload extends Omit<AdcmPostOperationPayload, 'operation'> {
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

export interface AdcmPostLastStepOperationPayload {
  postOperationPayload: AdcmPostOperationPayload;
  lastStepPayload: RunDynamicActionArgs;
}

export interface PostOperationWithStepResetPayload {
  stepId: number;
  postOperationPayload: AdcmPostOperationPayload;
}

type SomeEntityApiArgs<T> = SomeEntityArgs & T;

export type GetProcessApiArgs = SomeEntityApiArgs<GetWizardProcessPayload>;
export type GetStepApiArgs = SomeEntityApiArgs<GetWizardStepPayload>;
export type CreateProcessApiArgs = SomeEntityApiArgs<CreateWizardProcessPayload>;
export type CreateOperationApiArgs = SomeEntityApiArgs<PostWizardOperationPayload>;
export type RunDynamicActionApiArgs = SomeEntityApiArgs<RunDynamicActionPayload>;

export interface EntityWizardApi {
  getProcess(args: GetProcessApiArgs): Promise<AdcmActionWizardProcess>;
  getStep(args: GetStepApiArgs, options?: RequestOptions): Promise<AdcmActionProcessStep>;
  createProcess(args: CreateProcessApiArgs): Promise<AdcmActionWizardProcess>;
  createOperation(args: CreateOperationApiArgs): Promise<AdcmWizardProcessOperation>;
  runDynamicAction(args: RunDynamicActionApiArgs): Promise<void>;
}
