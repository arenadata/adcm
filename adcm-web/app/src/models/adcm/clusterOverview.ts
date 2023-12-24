import { AdcmClusterStatus } from '@models/adcm/cluster';

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
  servicesStatus: AdcmClusterStatus;
}

export interface AdcmClusterOverviewHostsFilter {
  hostsStatus: AdcmClusterStatus;
}
