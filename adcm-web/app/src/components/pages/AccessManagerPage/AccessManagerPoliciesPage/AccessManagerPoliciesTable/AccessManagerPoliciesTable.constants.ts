import { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'Description',
    name: 'description',
  },
  {
    label: 'Role',
    name: 'role',
  },
  {
    label: 'Groups',
    name: 'group',
  },
  {
    label: 'Objects',
    name: 'objects',
  },
  {
    // label and name are empty because it's column for expand button:
    label: '',
    name: '',
    width: '80px',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];
