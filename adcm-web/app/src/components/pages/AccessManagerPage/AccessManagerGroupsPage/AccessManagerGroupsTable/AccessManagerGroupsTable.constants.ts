import { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    isCheckAll: true,
    name: 'checkAll',
  },
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'Description',
    name: 'description',
    isSortable: false,
  },
  {
    label: 'Users',
    name: 'users',
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
