import { AdcmHost } from '@models/adcm/host';
import { AdcmComponent } from '@models/adcm/clusterMapping';

export interface AdcmClusterHost extends AdcmHost {
  components: AdcmComponent[];
}

export interface AdcmClusterHostsFilter {
  name?: string;
  hostprovider?: string;
}
