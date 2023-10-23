import { AdcmServiceComponentPrototype } from './clusterServiceComponent';
import { AdcmMaintenanceMode } from './maintenanceMode';

export interface AdcmMapping {
  id?: number;
  hostId: number;
  componentId: number;
}

export interface AdcmHostShortView {
  id: number;
  name: string;
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
}

interface AdcmComponentDependencyLicense {
  status: string;
  text: string;
}

export interface AdcmComponentDependency {
  id: number;
  name: string;
  displayName: string;
  componentPrototypes?: AdcmComponentDependency[];
  license: AdcmComponentDependencyLicense;
}

export type AdcmComponentConstraint = number | string;

export interface AdcmComponentService {
  id: number;
  name: string;
  displayName: string;
}

export interface AdcmComponentPrototype {
  id: number;
  name: string;
  displayName: string;
  version: string;
}

export interface AdcmComponent {
  id: number;
  name: string;
  displayName: string;
  isMaintenanceModeAvailable: boolean;
  maintenanceMode: AdcmMaintenanceMode;
  constraints: AdcmComponentConstraint[];
  service: AdcmComponentService;
  dependOn: AdcmComponentDependency[] | null;
  prototype?: AdcmServiceComponentPrototype;
}

export interface CreateMappingPayload {
  id: number;
  hostId: number;
  componentId: number;
}
