import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Subjob',
    name: 'displayName',
  },
  {
    label: 'Status',
    name: 'status',
  },
  {
    label: 'Duration',
    name: 'duration',
  },
  {
    label: 'Start time',
    name: 'startTime',
  },
  {
    label: 'Finish time',
    name: 'endTime',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];
