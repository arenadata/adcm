import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    isCheckAll: true,
    name: 'checkAll',
  },
  {
    label: 'Username',
    name: 'username',
    isSortable: true,
  },
  {
    label: 'Status',
    name: 'status',
    isSortable: false,
  },
  {
    label: 'Email',
    name: 'email',
    isSortable: false,
  },
  {
    label: 'Group',
    name: 'group',
    isSortable: false,
  },
  {
    label: 'Type',
    name: 'type',
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
