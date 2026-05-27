export enum AdcmJobStatus {
  Created = 'created',
  Success = 'success',
  Failed = 'failed',
  Running = 'running',
  Locked = 'locked',
  Aborted = 'aborted',
  Broken = 'broken',
  Info = 'info',
  Warning = 'warning',
  Revoked = 'revoked',
  Queued = 'queued',
  Scheduled = 'scheduled',
}

export enum AdcmJobObjectType {
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Provider = 'provider',
  Host = 'host',
  Component = 'component',
  ActionHostGroup = 'action_host_group',
}

export interface AdcmJobObject {
  id: number;
  name: string;
  type: AdcmJobObjectType;
  displayName?: string;
}

export interface AdcmJobObjectAdvanced extends AdcmJobObject {
  link: string;
}

export interface AdcmJob {
  id: number;
  name: string | null;
  displayName: string | null;
  status: AdcmJobStatus;
  objects: AdcmJobObject[];
  duration: number | null;
  startTime: string | null;
  endTime: string | null;
  isTerminatable: boolean;
  description: string | null;
  childJobs: AdcmSubJob[];
  action: {
    id: number;
    name: string;
    displayName?: string;
  } | null;
}

export interface AdcmSubJob {
  id: number;
  name: string;
  displayName: string;
  status: AdcmJobStatus;
  startTime: string | null;
  endTime: string | null;
  duration: number | null;
  isTerminatable: boolean;
}

export interface AdcmSubJobDetails extends AdcmSubJob {
  parentTask: AdcmJob;
}

export enum AdcmSubJobLogSeverity {
  Error = 'error',
  Warning = 'warning',
  Info = 'info',
}

export type AdcmSubJobLogCheckContentItem = {
  message: string;
  result: boolean;
  title: string;
  type: 'group' | 'check';
  severity?: AdcmSubJobLogSeverity;
  content?: AdcmSubJobLogCheckContentItem[];
};

export interface AdcmSubJobLogCheckContentItemWithJobStatus extends AdcmSubJobLogCheckContentItem {
  subJobStatus?: string;
}

export enum AdcmSubJobLogType {
  Stdout = 'stdout',
  Stderr = 'stderr',
  Check = 'check',
  Custom = 'custom',
}

interface AdcmSubJobLogItemCommon {
  id: number;
  name: string;
  format: string;
}
export interface AdcmSubJobLogItemCheck extends AdcmSubJobLogItemCommon {
  type: AdcmSubJobLogType.Check;
  content: AdcmSubJobLogCheckContentItem[];
}
export interface AdcmSubJobLogItemStd extends AdcmSubJobLogItemCommon {
  type: AdcmSubJobLogType.Stdout | AdcmSubJobLogType.Stderr;
  content: string;
}
export interface AdcmSubJobLogItemCustom extends AdcmSubJobLogItemCommon {
  type: AdcmSubJobLogType.Custom;
  content: string;
}

export type AdcmSubJobLogItem = AdcmSubJobLogItemCheck | AdcmSubJobLogItemStd | AdcmSubJobLogItemCustom;

export interface AdcmJobsFilter {
  jobName?: string;
  objectName?: string;
  status?: AdcmJobStatus;
}

export interface AdcmRestartJobPayload {
  id: number;
}
