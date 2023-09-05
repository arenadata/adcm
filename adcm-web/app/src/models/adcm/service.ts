import { AdcmConcerns } from '@models/adcm/concern';
import { AdcmMaintenanceMode } from '@models/adcm/maintenanceMode';
import { AdcmPrototypeType } from '@models/adcm/prototype';

export enum AdcmServiceStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmService {
  id: number;
  name: string;
  displayName: string;
  prototype: AdcmServicePrototype;
  status: AdcmServiceStatus;
  state: string;
  concerns: AdcmConcerns[];
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
  mainInfo: string;
  cluster: {
    id: number;
    name: string;
  };
}

export interface AdcmServicePrototype {
  id: number;
  name: string;
  displayName: string;
  type: AdcmPrototypeType.Service;
  version: string;
}

export interface AdcmServicesFilter {
  serviceName?: string;
}

export interface AdcmRelatedServiceComponentsState {
  id: number;
  name: string;
  displayName?: string;
  status: AdcmServiceStatus;
}

export interface AdcmRelatedServiceComponentsStates {
  components: AdcmRelatedServiceComponentsState[];
}
