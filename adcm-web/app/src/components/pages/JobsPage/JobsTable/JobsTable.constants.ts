import { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: '№',
    name: 'id',
    isSortable: true,
  },
  {
    label: 'Name',
    name: 'name',
    isSortable: false,
  },
  {
    label: 'Status',
    name: 'status',
    isSortable: false,
  },
  {
    label: 'Objects',
    name: 'objects',
    isSortable: false,
  },
  {
    label: 'Duration',
    name: 'duration',
    isSortable: false,
  },
  {
    label: 'Start time',
    name: 'startTime',
    isSortable: false,
  },
  {
    label: 'End time',
    name: 'endTime',
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
