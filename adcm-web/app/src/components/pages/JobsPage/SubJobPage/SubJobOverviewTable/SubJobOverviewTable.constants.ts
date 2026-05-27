import { AdcmJobStatus } from '@models/adcm';
import type { BaseStatus, TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Object',
    name: 'objects',
  },
  {
    label: 'Status',
    name: 'status',
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
    label: 'End time',
    name: 'endTime',
  },
  {
    label: 'Actions',
    name: 'actions',
  },
];

export const jobStatusesMap: { [key in AdcmJobStatus]: BaseStatus } = {
  [AdcmJobStatus.Created]: 'created',
  [AdcmJobStatus.Running]: 'running',
  [AdcmJobStatus.Queued]: 'running',
  [AdcmJobStatus.Scheduled]: 'running',
  [AdcmJobStatus.Success]: 'success',
  [AdcmJobStatus.Failed]: 'failed',
  [AdcmJobStatus.Revoked]: 'failed',
  [AdcmJobStatus.Aborted]: 'aborted',
  [AdcmJobStatus.Locked]: 'locked',
  [AdcmJobStatus.Broken]: 'broken',
  [AdcmJobStatus.Info]: 'info',
  [AdcmJobStatus.Warning]: 'warning',
};
