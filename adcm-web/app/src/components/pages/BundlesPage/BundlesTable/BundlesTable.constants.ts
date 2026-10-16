import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    isCheckAll: true,
    name: 'checkAll',
  },
  {
    label: 'Product',
    name: 'displayName',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
  },
  {
    label: 'Edition',
    name: 'edition',
  },
  {
    label: 'Date uploaded',
    name: 'uploadTime',
    isSortable: true,
  },
  {
    label: 'License',
    name: 'license',
  },
  {
    label: 'Signature',
    name: 'signatureStatus',
  },
  {
    label: 'Operations',
    name: 'operations',
    headerAlign: 'center',
    width: '100px',
  },
];
