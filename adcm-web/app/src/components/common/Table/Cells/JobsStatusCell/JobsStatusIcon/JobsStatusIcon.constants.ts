import { AdcmJobStatus } from '@models/adcm';
import { IconsNames } from '@uikit';

export const jobStatusesIconsMap: { [key in AdcmJobStatus]: IconsNames } = {
  [AdcmJobStatus.CREATED]: 'g2-created-10x10',
  [AdcmJobStatus.SUCCESS]: 'g2-success-10x10',
  [AdcmJobStatus.FAILED]: 'g2-failed-10x10',
  [AdcmJobStatus.RUNNING]: 'g2-running-10x10',
  [AdcmJobStatus.LOCKED]: 'g2-locked-10x10',
  [AdcmJobStatus.ABORTED]: 'g2-aborted-10x10',
};
