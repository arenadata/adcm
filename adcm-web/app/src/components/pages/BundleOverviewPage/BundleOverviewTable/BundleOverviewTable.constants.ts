import type { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Product',
    name: 'name',
    isSortable: false,
  },
  {
    label: 'Version',
    name: 'version',
    isSortable: false,
  },
  {
    label: 'License status',
    name: 'licenseStatus',
    isSortable: false,
  },
  {
    label: 'License text',
    name: 'licenseText',
    isSortable: false,
  },
];
