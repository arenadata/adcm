import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'displayName',
    isSortable: true,
  },
  {
    label: 'Description',
    name: 'description',
  },
  {
    label: 'Permissions',
    name: 'permissions',
  },
  {
    label: '',
    name: '',
    width: '80px',
  },
  {
    label: 'Operations',
    name: 'operations',
    headerAlign: 'center',
    width: '100px',
  },
];
