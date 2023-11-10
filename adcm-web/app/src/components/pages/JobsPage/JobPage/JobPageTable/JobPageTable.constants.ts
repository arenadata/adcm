import { AdcmJobStatus } from '@models/adcm';
import { BaseStatus, TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Object',
    name: 'objects',
  },
  {
    label: 'Duration',
    name: 'duration',
  },
  {
    label: 'Start time',
    name: 'startTime',
  },
  {
    label: 'Finish time',
    name: 'endTime',
  },
  {
    label: 'Logs',
    name: 'actions',
  },
];

export const jobStatusesMap: { [key in AdcmJobStatus]: BaseStatus } = {
  [AdcmJobStatus.Created]: 'created',
  [AdcmJobStatus.Running]: 'running',
  [AdcmJobStatus.Success]: 'success',
  [AdcmJobStatus.Failed]: 'failed',
  [AdcmJobStatus.Aborted]: 'aborted',
  [AdcmJobStatus.Locked]: 'locked',
};
