export enum AdcmConcernCause {
  Config = 'config',
  HostComponent = 'host-component',
  Import = 'import',
  Service = 'service',
  Requirement = 'requirement',
  Job = 'job',
}

export enum AdcmConcernType {
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Host = 'host',
  Provider = 'provider',
  Job = 'job',
  Prototype = 'prototype',
}

export interface AdcmConcernCommonPlaceholder {
  name: string;
}

export interface AdcmConcernClusterPlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Cluster;
  params: {
    clusterId: number;
  };
}

export interface AdcmConcernServicePlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Service;
  params: {
    clusterId: number;
    serviceId: number;
  };
}

export interface AdcmConcernComponentPlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Component;
  params: {
    clusterId: number;
    serviceId: number;
    componentId: number;
  };
}

export interface AdcmConcernHostPlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Host;
  params: {
    hostId: number;
  };
}

export interface AdcmConcernHostProviderPlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Provider;
  params: {
    providerId: number;
  };
}

export interface AdcmConcernJobPlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Job;
  params: {
    jobId: number;
  };
}

export interface AdcmConcernPrototypePlaceholder extends AdcmConcernCommonPlaceholder {
  type: AdcmConcernType.Prototype;
  params: {
    prototypeId: number;
  };
}

export type AdcmConcernPlaceholder =
  | AdcmConcernClusterPlaceholder
  | AdcmConcernServicePlaceholder
  | AdcmConcernComponentPlaceholder
  | AdcmConcernHostPlaceholder
  | AdcmConcernHostProviderPlaceholder
  | AdcmConcernJobPlaceholder
  | AdcmConcernPrototypePlaceholder;

export interface AdcmConcernReason {
  message: string;
  placeholder: Record<string, AdcmConcernPlaceholder>;
}

export interface AdcmConcerns {
  id: number;
  reason: AdcmConcernReason;
  isBlocking: boolean;
  cause: AdcmConcernCause;
}
