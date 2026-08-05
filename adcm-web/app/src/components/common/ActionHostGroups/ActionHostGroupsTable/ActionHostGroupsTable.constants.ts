import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
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
    label: 'Operations',
    name: 'operations',
    headerAlign: 'center',
    width: '100px',
  },
];
