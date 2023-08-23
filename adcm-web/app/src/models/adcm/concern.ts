export enum AdcmConcernType {
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Host = 'host',
  Provider = 'provider',
  Job = 'job',
}

export interface AdcmConcernReasonPlaceholderInfo {
  clusterId?: number;
  serviceId?: number;
  componentId?: number;
  hostId?: number;
  hostproviderId?: number;
  name: string;
  type: AdcmConcernType;
}

export interface AdcmConcernReasonV2 {
  message: string;
  placeholder: {
    // TO_DO: mark source and target as optional and fix the concern component because of inevitable errors
    source: AdcmConcernReasonPlaceholderInfo;
    target: AdcmConcernReasonPlaceholderInfo;
    job?: {
      jobId?: number;
      name: string;
      type: AdcmConcernType.Job;
    };
  };
}

export interface AdcmConcernsV2 {
  id: number;
  reason: AdcmConcernReasonV2;
  isBlocking: boolean;
}

// TODO: remove these interfaces below and use the new ones above once the backend team fixes the format
export interface AdcmConcernReason {
  message: string;
  placeholder: {
    source: {
      id?: number;
      name: string;
      type: string;
    };
    target: {
      id?: number;
      name: string;
      type: string;
    };
  };
}

export interface AdcmConcerns {
  id: number;
  reason: AdcmConcernReason;
  isBlocking: boolean;
}
