import { AdcmConcerns, AdcmLicenseStatus, AdcmMaintenanceMode, AdcmPrototypeType } from '@models/adcm';

export enum AdcmServiceStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmServiceDependOnServiceComponent {
  id: number;
  name: string;
  displayName: string;
  version: string;
}

export interface AdcmServiceDependOnService {
  servicePrototype: Omit<AdcmServicePrototype, 'dependOn' | 'isRequired'> & {
    componentPrototypes: AdcmServiceDependOnServiceComponent[];
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

export interface AdcmServicePrototype {
  id: number;
  name: string;
  displayName: string;
  type: AdcmPrototypeType.Service;
  version: string;
  license: {
    status: AdcmLicenseStatus;
    text: string;
  };
  isRequired: boolean;
  dependOn: AdcmServiceDependOnService[] | null;
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
