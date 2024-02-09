import { AdcmConcerns } from './concern';
import { AdcmEntityState } from './common';
import { AdcmHostProvider } from './hostProvider';

export enum AdcmHostStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmHostsFilter {
  name?: string;
  hostproviderName?: string;
  clusterName?: string;
}

export interface AdcmHostComponentsFilter {
  displayName?: string;
}

export interface AdcmHostPrototype {
  id: number;
  name: string;
  displayName: string;
  type: string;
  version: string;
}

export interface AdcmHost {
  id: number;
  name: string;
  state: AdcmEntityState;
  multiState: string[];
  status: AdcmHostStatus;
  hostprovider: AdcmHostProvider;
  prototype: AdcmHostPrototype;
  concerns: AdcmConcerns[];
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: string;
  cluster: {
    id: number;
    name: string;
  };
}

export interface CreateAdcmHostPayload {
  clusterId?: number | null;
  hostproviderId: number | null;
  name: string;
}

export interface AdcmUpdatePayload {
  name: string;
}

export type AdcmHostCandidate = Pick<AdcmHost, 'id' | 'name'>;
