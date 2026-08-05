import { AdcmServiceComponentStatus } from '@models/adcm';
import type { BaseStatus, TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
  },
  {
    label: 'Hosts',
    name: 'Hosts',
  },
  {
    label: 'Concerns',
    name: 'concerns',
  },
  {
    label: 'Operations',
    name: 'operations',
    headerAlign: 'center',
    width: '100px',
  },
  {
    label: '',
    name: '',
    width: '24px',
  },
];

export const serviceComponentStatusMap: { [key in AdcmServiceComponentStatus]: BaseStatus } = {
  [AdcmServiceComponentStatus.Up]: 'done',
  [AdcmServiceComponentStatus.Down]: 'unknown',
};
