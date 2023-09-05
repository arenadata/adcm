import { AdcmConcerns } from '@models/adcm/concern';
import { AdcmHostProvider } from '@models/adcm';

export enum AdcmHostStatus {
  On = 'done',
  Off = 'failed',
}

export interface AdcmHostsFilter {
  hostName?: string;
  hostProvider?: string;
  clusterName?: string;
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
  state: string;
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
