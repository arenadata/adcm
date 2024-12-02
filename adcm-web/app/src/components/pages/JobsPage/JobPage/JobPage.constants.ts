import { AdcmJobStatus } from '@models/adcm';
import type { BaseStatus } from '@uikit';

export const jobStatusesMap: { [key in AdcmJobStatus]: BaseStatus } = {
  [AdcmJobStatus.Created]: 'created',
  [AdcmJobStatus.Running]: 'running',
  [AdcmJobStatus.Success]: 'success',
  [AdcmJobStatus.Failed]: 'failed',
  [AdcmJobStatus.Aborted]: 'aborted',
  [AdcmJobStatus.Locked]: 'locked',
  [AdcmJobStatus.Broken]: 'broken',
};
