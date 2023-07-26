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
  status: number;
  provider: AdcmHostProvider;
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
  clusterName: string;
  hostProvider: string;
  hostName: string;
}
