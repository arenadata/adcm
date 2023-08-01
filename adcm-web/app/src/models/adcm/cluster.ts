import { AdcmConcerns } from './concern';

export enum AdcmClusterStatus {
  Up = 'UP',
  Down = 'DOWN',
}

export interface AdcmClusterPrototype {
  id: number;
  name: string;
  displayName: string;
  type: string;
  version: string;
}

export interface AdcmCluster {
  id: number;
  name: string;
  state: string;
  multiState: string[];
  status: AdcmClusterStatus;
  prototype: AdcmClusterPrototype;
  description: string;
  concerns: AdcmConcerns[];
  isUpgradable: boolean;
  mainInfo: string;
}

export interface AdcmClustersFilter {
  clusterName?: string;
  clusterStatus?: AdcmClusterStatus;
  prototypeName?: string;
}

export interface CreateAdcmClusterPayload {
  isLicenseAccepted: boolean;
  prototypeId: number;
  name: string;
  description: string;
}

export interface UpdateAdcmClusterPayload {
  name: string;
}

export interface AdcmClusterUpgrade {
  id: number;
  name: string;
  displayName: string;
  isLicenseAccepted: boolean;
}

export interface AdcmClusterActionDetails {
  isAllowToTerminate: boolean;
  hostComponentMapRules: object[];
  disclaimer: string;
  config: {
    config: object[];
    attr: object;
  };
}

export interface AdcmClusterActionPayload {
  hostComponentMap: {
    id: number;
    hostId: number;
    componentId: number;
    serviceId: number;
  }[];
  config: unknown;
  isVerbose: boolean;
}
