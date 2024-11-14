import type { AdcmConcerns } from './concern';
import type { AdcmLicense } from './license';
import type { AdcmPrototypeShortView, AdcmPrototypeType } from './prototype';
import type { AdcmMaintenanceMode } from './maintenanceMode';

export enum AdcmServiceStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmComponentDependency extends AdcmPrototypeShortView {
  license: AdcmLicense;
  componentPrototypes: AdcmPrototypeShortView[];
}

export interface AdcmDependOnService {
  servicePrototype: AdcmComponentDependency;
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

export interface AdcmServicePrototype extends AdcmPrototypeShortView {
  type: AdcmPrototypeType.Service;
  license: AdcmLicense;
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
