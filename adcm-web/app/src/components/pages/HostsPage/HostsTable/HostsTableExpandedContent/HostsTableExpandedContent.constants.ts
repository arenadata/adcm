import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
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
