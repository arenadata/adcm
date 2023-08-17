export enum AdcmJobStatus {
  CREATED = 'created',
  SUCCESS = 'success',
  FAILED = 'failed',
  RUNNING = 'running',
  LOCKED = 'locked',
  ABORTED = 'aborted',
}

export enum AdcmJobObjectType {
  ADCM = 'adcm',
  CLUSTER = 'cluster',
  SERVICE = 'service',
  PROVIDER = 'provider',
  HOST = 'host',
  COMPONENT = 'component',
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
  duration: string;
  startTime: string;
  endTime: string;
  isTerminatable: boolean;
  childJobs?: [];
}

export interface AdcmJobsFilter {
  name?: string;
  object?: string;
  status?: AdcmJobStatus;
}

export interface AdcmRestartJobPayload {
  id: number;
}
