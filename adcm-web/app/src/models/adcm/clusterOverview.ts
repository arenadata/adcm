import type { AdcmClusterStatus } from './cluster';
import type { AdcmHostStatus } from './host';
import type { AdcmServiceStatus } from './service';

export interface AdcmClusterOverviewStatusService {
  id: number;
  name: string;
  displayName: string;
  status: AdcmClusterStatus;
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
}

export interface AdcmClusterOverviewServicesFilter {
  servicesStatus: AdcmServiceStatus | undefined;
}

export interface AdcmClusterOverviewHostsFilter {
  hostsStatus: AdcmHostStatus | undefined;
}
