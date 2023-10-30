import { AdcmHost } from '@models/adcm/host';
import { AdcmMappingComponent } from '@models/adcm/clusterMapping';

export interface AdcmClusterHost extends AdcmHost {
  components: AdcmMappingComponent[];
}

export interface AdcmClusterHostsFilter {
  name?: string;
  hostprovider?: string;
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
