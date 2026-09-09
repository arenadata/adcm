export type AdcmCapacityUnit = 'B' | 'KiB' | 'MiB' | 'GiB' | 'TiB' | 'PiB';

export interface AdcmResourceValue {
  value: number;
  unit: AdcmCapacityUnit;
}

export interface AdcmClusterResources {
  cpuVcores: number;
  ram: AdcmResourceValue;
  disk: AdcmResourceValue;
}

export interface AdcmClusterEntityMetrics {
  count: number;
  up: number;
  down: number;
  maintenanceMode: number;
}

export interface AdcmClusterMetrics {
  id: number;
  resources: AdcmClusterResources;
  services?: AdcmClusterEntityMetrics;
  hosts?: AdcmClusterEntityMetrics;
}
