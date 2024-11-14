import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Configuration group',
    name: 'name',
  },
  {
    label: 'Description',
    name: 'description',
  },
  {
    label: 'Hosts',
    name: 'hosts',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];
