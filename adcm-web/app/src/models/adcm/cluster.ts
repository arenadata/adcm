import type { AdcmConcerns } from './concern';
import type { AdcmEntityState } from './common';

export enum AdcmClusterStatus {
  Up = 'up',
  Down = 'down',
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
  state: AdcmEntityState;
  multiState: string[];
  status: AdcmClusterStatus;
  prototype: AdcmClusterPrototype;
  description: string;
  concerns: AdcmConcerns[];
  isUpgradable: boolean;
  mainInfo: string;
}

export interface AdcmClustersFilter {
  name?: string;
  status?: AdcmClusterStatus;
  prototypeName?: string;
}

export interface CreateAdcmClusterPayload {
  prototypeId: number;
  name: string;
  description: string;
}

export interface RenameAdcmClusterPayload {
  name: string;
}
