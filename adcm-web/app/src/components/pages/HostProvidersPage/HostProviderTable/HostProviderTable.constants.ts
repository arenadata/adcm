import { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'Type',
    name: 'type',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: true,
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
