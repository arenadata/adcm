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
    label: 'Concern',
    name: 'concern',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];

export const hostStatusesMap: { [key in AdcmHostStatus]: BaseStatus } = {
  [AdcmHostStatus.On]: 'done',
  [AdcmHostStatus.Off]: 'failed',
};
