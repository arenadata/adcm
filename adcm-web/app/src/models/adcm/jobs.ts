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

interface AdcmJobObject {
  id: number;
  name: string;
  type: AdcmJobObjectType;
  displayName?: string;
}

export interface AdcmJob {
  id: number;
  name: string;
  displayName: string;
  status: AdcmJobStatus;
  objects: AdcmJobObject[];
  duration: number;
  startTime: string;
  endTime: string;
  isTerminatable: boolean;
  childJobs?: AdcmJob[];
  logs?: AdcmJobLog[];
}

export interface AdcmJobLog {
  id: number;
  name: string;
  type: string;
  format: string;
  content: string;
}

export interface AdcmJobsFilter {
  name?: string;
  object?: string;
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
