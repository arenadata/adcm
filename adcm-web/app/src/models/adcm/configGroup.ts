import type { AdcmHostCandidate } from './host';

export interface AdcmConfigGroup {
  id: number;
  name: string;
  description: string;
  hosts: AdcmHostCandidate[];
}
