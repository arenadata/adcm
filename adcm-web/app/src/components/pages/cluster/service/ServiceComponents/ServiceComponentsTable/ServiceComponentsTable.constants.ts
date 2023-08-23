import { TableColumn, BaseStatus } from '@uikit';
import { AdcmServiceComponentStatus } from '@models/adcm';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
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
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];

export const serviceComponentsStatusMap: { [key in AdcmServiceComponentStatus]: BaseStatus } = {
  [AdcmServiceComponentStatus.Up]: 'done',
  [AdcmServiceComponentStatus.Down]: 'unknown',
};
