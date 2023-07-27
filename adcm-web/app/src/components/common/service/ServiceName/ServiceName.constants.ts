import { AdcmServiceStatus } from '@models/adcm';
import { BaseStatus } from '@uikit';

export const serviceStatusesMap: { [key in AdcmServiceStatus]: BaseStatus } = {
  [AdcmServiceStatus.Up]: 'done',
  [AdcmServiceStatus.Down]: 'unknown',
};
