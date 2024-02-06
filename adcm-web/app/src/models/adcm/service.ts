import { AdcmConcerns } from './concern';
import { AdcmLicense, AdcmLicenseStatus } from './license';
import { AdcmPrototypeShortView, AdcmPrototypeType } from './prototype';
import { AdcmMaintenanceMode } from './maintenanceMode';

export enum AdcmServiceStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmDependOnService {
  servicePrototype: AdcmPrototypeShortView & {
    license: AdcmLicense;
    componentPrototypes: AdcmPrototypeShortView[];
  };
}

export interface AdcmService {
  id: number;
  name: string;
  displayName: string;
  prototype: AdcmServicePrototype;
  status: AdcmServiceStatus;
  state: string;
  multiState: string[];
  concerns: AdcmConcerns[];
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
  mainInfo: string;
  cluster: {
    id: number;
    name: string;
  };
}

export type ServicePrototypeId = AdcmServicePrototype['id'];

export interface AdcmServicePrototype {
  id: number;
  name: string;
  displayName: string;
  type: AdcmPrototypeType.Service;
  version: string;
  license: {
    status: AdcmLicenseStatus;
    text: string | null;
  };
  isRequired: boolean;
  dependOn: AdcmDependOnService[] | null;
}

export interface AdcmServicesFilter {
  displayName?: string;
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
