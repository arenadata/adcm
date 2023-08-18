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

export interface AdcmComponentDependency {
  prototypeId: number;
  name: string;
  displayName: string;
  components?: AdcmComponentDependency[];
}

export type AdcmComponentConstraint = number | string;

export interface AdcmComponentService {
  id: number;
  name: string;
  displayName: string;
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
}

export interface CreateMappingPayload {
  id: number;
  hostId: number;
  componentId: number;
}
