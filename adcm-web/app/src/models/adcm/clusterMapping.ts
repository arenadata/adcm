import type { AdcmMaintenanceMode } from './maintenanceMode';
import type { AdcmDependOnService, AdcmServicePrototype } from './service';
import type { AdcmPrototypeShortView } from './prototype';
import type { AdcmEntityState } from './common';

export interface AdcmMapping {
  id?: number;
  hostId: number;
  componentId: number;
}

export type HostId = AdcmHostShortView['id'];

export interface AdcmHostShortView {
  id: number;
  name: string;
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
}

export type AdcmComponentConstraint = number | string;

export type ServiceId = AdcmMappingComponentService['id'];

export interface AdcmMappingComponentService {
  id: number;
  name: string;
  displayName: string;
  state: AdcmEntityState;
  prototype: AdcmPrototypeShortView;
}

export type ComponentId = AdcmMappingComponent['id'];

export interface AdcmMappingComponent {
  id: number;
  name: string;
  displayName: string;
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
  constraints: AdcmComponentConstraint[];
  service: AdcmMappingComponentService;
  prototype: AdcmPrototypeShortView;
  dependOn: AdcmDependOnService[] | null;
}

export interface CreateMappingPayload {
  id: number;
  hostId: number;
  componentId: number;
}

export type NotAddedServicesDictionary = Record<ServiceId, AdcmServicePrototype>;
