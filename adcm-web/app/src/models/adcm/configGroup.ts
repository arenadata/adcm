import { AdcmHostCandidate } from '@models/adcm/host';

export interface AdcmConfigGroup {
  id: number;
  name: string;
  description: string;
  hosts: AdcmHostCandidate[];
}
