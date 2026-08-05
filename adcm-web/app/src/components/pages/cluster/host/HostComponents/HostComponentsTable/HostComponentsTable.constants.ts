import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'displayName',
    isSortable: true,
  },
  {
    label: 'Concerns',
    name: 'concerns',
  },
  {
    label: 'Operations',
    name: 'operations',
    headerAlign: 'center',
    width: '100px',
  },
];
