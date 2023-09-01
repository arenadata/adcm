import { AdcmJobStatus } from '@models/adcm';
import { IconsNames } from '@uikit';

export const jobStatusesIconsMap: { [key in AdcmJobStatus]: IconsNames } = {
  [AdcmJobStatus.Created]: 'g2-created-10x10',
  [AdcmJobStatus.Success]: 'g2-success-10x10',
  [AdcmJobStatus.Failed]: 'g2-failed-10x10',
  [AdcmJobStatus.Running]: 'g2-running-10x10',
  [AdcmJobStatus.Locked]: 'g2-locked-10x10',
  [AdcmJobStatus.Aborted]: 'g2-aborted-10x10',
};
