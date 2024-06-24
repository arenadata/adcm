import type { AdcmHost } from './host';
import type { AdcmMappingComponent } from './clusterMapping';

export interface AdcmClusterHost extends AdcmHost {
  components: AdcmMappingComponent[];
}

export interface AdcmClusterHostsFilter {
  name?: string;
  hostproviderName?: string;
  componentId?: string;
}

export interface AddClusterHostsPayload {
  clusterId: number;
  selectedHostIds: number[];
}

export enum AdcmClusterHostComponentsStatus {
  Up = 'up',
  Down = 'down',
}

export interface AdcmClusterHostComponentsState {
  id: number;
  name: string;
  status: AdcmClusterHostComponentsStatus;
}

export interface AdcmClusterHostComponentsStates {
  hostComponents: AdcmClusterHostComponentsState[];
}
