import { TableColumn, BaseStatus } from '@uikit';
import { AdcmClusterStatus } from '@models/adcm';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: false,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: false,
  },
  {
    label: 'Product',
    name: 'product',
    isSortable: false,
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
  },
];

export const clusterStatusesMap: { [key in AdcmClusterStatus]: BaseStatus } = {
  UP: 'done',
  DOWN: 'unknown',
};
