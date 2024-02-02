import { AdcmConcerns } from '@models/adcm/concern';
import { AdcmLicense, AdcmLicenseStatus } from '@models/adcm/license';
import { AdcmPrototypeShortView, AdcmPrototypeType } from '@models/adcm/prototype';
import { AdcmMaintenanceMode } from '@models/adcm/maintenanceMode';

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
