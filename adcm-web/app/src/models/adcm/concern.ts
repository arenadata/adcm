export enum AdcmConcernCause {
  Config = 'config',
  HostComponent = 'host-component',
  Import = 'import',
  Service = 'service',
  Requirement = 'requirement',
  Job = 'job',
}

export enum AdcmConcernOwnerType {
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Host = 'host',
  Provider = 'provider',
}

export enum AdcmConcernType {
  AdcmConfig = 'adcm_config',
  ClusterConfig = 'cluster_config',
  ComponentConfig = 'component_config',
  HostConfig = 'host_config',
  ProviderConfig = 'provider_config',
  ServiceConfig = 'service_config',
  ClusterServices = 'cluster_services', // the same value for the type "Requirement"
  ClusterImport = 'cluster_import',
  HostComponent = 'cluster_mapping',
  Job = 'job',
  Prototype = 'prototype',
  Adcm = 'adcm',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Provider = 'provider',
  Host = 'host',
}

export interface AdcmConcernCommonPlaceholder {
  name: string;
  type: AdcmConcernType;
}

export interface AdcmConcernClusterPlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    clusterId: number;
  };
}

export interface AdcmConcernServicePlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    clusterId: number;
    serviceId: number;
  };
}

export interface AdcmConcernComponentPlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    clusterId: number;
    serviceId: number;
    componentId: number;
  };
}

export interface AdcmConcernHostPlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    hostId: number;
  };
}

export interface AdcmConcernHostProviderPlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    providerId: number;
  };
}

export interface AdcmConcernJobPlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    jobId: number;
  };
}

export interface AdcmConcernPrototypePlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    prototypeId: number;
  };
}

export interface AdcmPrototypePlaceholder extends AdcmConcernCommonPlaceholder {
  params: {
    adcmId: number;
  };
}

export type AdcmConcernPlaceholder =
  | AdcmPrototypePlaceholder
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

interface AdcmConcernOwner {
  id: number;
  type: AdcmConcernOwnerType;
}

export interface AdcmConcerns {
  id: number;
  reason: AdcmConcernReason;
  isBlocking: boolean;
  cause: AdcmConcernCause;
  owner: AdcmConcernOwner;
}
