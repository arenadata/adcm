import { TableColumn, BaseStatus } from '@uikit';
import { AdcmClusterStatus } from '@models/adcm';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: false,
  },
  {
    label: 'Product',
    name: 'prototype',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
    isSortable: false,
  },
  {
    label: 'Description',
    name: 'description',
    isSortable: false,
  },
  {
    label: 'Concerns',
    name: 'concerns',
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

export const clusterStatusesMap: { [key in AdcmClusterStatus]: BaseStatus } = {
  [AdcmClusterStatus.Up]: 'done',
  [AdcmClusterStatus.Down]: 'unknown',
};
