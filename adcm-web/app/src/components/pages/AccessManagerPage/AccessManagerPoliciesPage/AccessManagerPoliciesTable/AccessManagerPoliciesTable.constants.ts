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
    label: 'Group',
    name: 'group',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];
