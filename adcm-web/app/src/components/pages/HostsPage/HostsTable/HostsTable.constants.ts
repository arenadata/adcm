import { BaseStatus, TableColumn } from '@uikit';
import { AdcmHostStatus } from '@models/adcm/host';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'hostName',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: false,
  },
  {
    label: 'Hostprovider',
    name: 'hostProvider',
    isSortable: false,
  },
  {
    label: 'Cluster',
    name: 'clusterName',
    isSortable: false,
  },
  {
    label: 'Concern',
    name: 'concern',
    isSortable: false,
  },
  {
    label: 'Actions',
    name: 'actions',
    isSortable: false,
    headerAlign: 'center',
    width: '100px',
  },
];

export const hostStatusesMap: { [key in AdcmHostStatus]: BaseStatus } = {
  [AdcmHostStatus.On]: 'done',
  [AdcmHostStatus.Off]: 'failed',
};
