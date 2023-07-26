import { AdcmConcerns } from './concern';

export enum AdcmClusterStatus {
  Up = 'UP',
  Down = 'DOWN',
}

export interface AdcmClusterPrototype {
  id: number;
  name: string;
  display_name: string;
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
