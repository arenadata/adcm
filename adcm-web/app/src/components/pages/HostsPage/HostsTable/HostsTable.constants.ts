import { BaseStatus, TableColumn } from '@uikit';
import { AdcmHostStatus } from '@models/adcm/host';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
  },
  {
    label: 'Hostprovider',
    name: 'hostProvider',
  },
  {
    label: 'Cluster',
    name: 'clusterName',
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

export const hostStatusesMap: { [key in AdcmHostStatus]: BaseStatus } = {
  [AdcmHostStatus.Up]: 'done',
  [AdcmHostStatus.Down]: 'unknown',
};
