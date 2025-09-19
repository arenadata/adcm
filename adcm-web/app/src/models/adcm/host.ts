import type { AdcmConcerns } from './concern';
import type { AdcmEntityState } from './common';
import type { AdcmHostProvider } from './hostProvider';
import type { AdcmMaintenanceMode } from './maintenanceMode';

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

interface AdcmHostCluster {
  id: number;
  name: string;
}

export interface AdcmHostDuplicate {
  id: number;
  name: string;
  cluster: AdcmHostCluster | null;
  concerns: AdcmConcerns[];
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
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
  cluster: AdcmHostCluster;
  duplicates: AdcmHostDuplicate[];
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

export interface CreateHostDuplicatePayload extends Omit<CreateAdcmHostPayload, 'hostproviderId'> {
  hostId: number;
}
