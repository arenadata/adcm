export enum AdcmJobStatus {
  Created = 'created',
  Success = 'success',
  Failed = 'failed',
  Running = 'running',
  Locked = 'locked',
  Aborted = 'aborted',
}

export enum AdcmJobObjectType {
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Provider = 'provider',
  Host = 'host',
  Component = 'component',
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
  name?: string;
  displayName?: string;
  status: AdcmJobStatus;
  objects: AdcmJobObject[];
  duration: number;
  startTime: string;
  endTime: string;
  isTerminatable: boolean;
  childJobs?: AdcmJob[];
  logs?: AdcmJobLogItem[];
}

export type AdcmJobLogCheckContentItem = {
  message: string;
  result: boolean;
  title: string;
  type: 'group' | 'check';
  content?: AdcmJobLogCheckContentItem[];
};

export interface AdcmJobLogCheckContentItemWithJobStatus extends AdcmJobLogCheckContentItem {
  jobStatus?: string;
}

export enum AdcmJobLogType {
  Stdout = 'stdout',
  Stderr = 'stderr',
  Check = 'check',
  Custom = 'custom',
}

interface AdcmJobLogItemCommon {
  id: number;
  name: string;
  format: string;
}
export interface AdcmJobLogItemCheck extends AdcmJobLogItemCommon {
  type: AdcmJobLogType.Check;
  content: AdcmJobLogCheckContentItem[];
}
export interface AdcmJobLogItemStd extends AdcmJobLogItemCommon {
  type: AdcmJobLogType.Stdout | AdcmJobLogType.Stderr;
  content: string;
}
export interface AdcmJobLogItemCustom extends AdcmJobLogItemCommon {
  type: AdcmJobLogType.Custom;
  content: string;
}

export type AdcmJobLogItem = AdcmJobLogItemCheck | AdcmJobLogItemStd | AdcmJobLogItemCustom;

export interface AdcmJobsFilter {
  jobName?: string;
  objectName?: string;
  status?: AdcmJobStatus;
}

export interface AdcmRestartJobPayload {
  id: number;
}

export interface AdcmTask {
  id: number;
  name: string;
  displayName: string;
  status: AdcmJobStatus;
  objects: AdcmJobObject[];
  duration: number;
  startTime: string;
  endTime: string;
  isTerminatable: boolean;
  childJobs: AdcmJob[];
}
