import { AdcmConcerns, AdcmLicenseStatus, AdcmMaintenanceMode, AdcmPrototypeType } from '@models/adcm';

export enum AdcmServiceStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmServiceDependOnServiceComponent {
  prototypeId: number;
  name: string;
  displayName: string;
}

export interface AdcmServiceDependOnService {
  prototypeId: number;
  name: string;
  displayName: string;
  components: AdcmServiceDependOnServiceComponent[];
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
  licenseStatus: AdcmLicenseStatus;
  isRequired: boolean;
  dependOn: AdcmServiceDependOnService[] | null;
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
