import type { AdcmClusterStatus } from './cluster';
import type { AdcmHostStatus } from './host';
import type { AdcmMaintenanceMode } from './maintenanceMode';
import type { AdcmServiceStatus } from './service';

export interface AdcmClusterOverviewStatusService {
  id: number;
  name: string;
  displayName: string;
  status: AdcmClusterStatus;
  maintenanceMode: AdcmMaintenanceMode;
  components: AdcmClusterOverviewStatusServiceComponent[];
}

export interface AdcmClusterOverviewStatusServiceComponent {
  id: number;
  name: string;
  status: AdcmClusterStatus;
  hosts: AdcmClusterOverviewStatusHost[];
}

export interface AdcmClusterOverviewStatusHost {
  id: number;
  name: string;
  displayName: string;
  status: AdcmClusterStatus;
  maintenanceMode: AdcmMaintenanceMode;
}

export interface AdcmClusterOverviewServicesFilter {
  servicesStatus: AdcmServiceStatus | undefined;
  maintenanceMode?: AdcmMaintenanceMode;
  displayName?: string;
}

export interface AdcmClusterOverviewHostsFilter {
  hostsStatus: AdcmHostStatus | undefined;
  maintenanceMode?: AdcmMaintenanceMode;
  name?: string;
}
