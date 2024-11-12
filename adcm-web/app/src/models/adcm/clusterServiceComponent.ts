import type { AdcmPrototypeShortView } from './prototype';
import type { AdcmConcerns } from './concern';
import type { AdcmMaintenanceMode } from './maintenanceMode';

export enum AdcmServiceComponentStatus {
  Up = 'up',
  Down = 'down',
}

export enum AdcmServiceComponentConcernType {
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Host = 'host',
  Provider = 'provider',
  Job = 'job',
}

export interface AdcmServiceComponentHost {
  id: number;
  name: string;
}

export interface AdcmServiceComponent {
  id: number;
  name: string;
  displayName: string;
  state: string;
  hosts: AdcmServiceComponentHost[];
  status: AdcmServiceComponentStatus;
  prototype: AdcmPrototypeShortView;
  cluster: {
    id: number;
    name: string;
  };
  service: {
    id: number;
    name: string;
    displayName: string;
  };
  concerns: AdcmConcerns[];
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
  mainInfo: string;
}
