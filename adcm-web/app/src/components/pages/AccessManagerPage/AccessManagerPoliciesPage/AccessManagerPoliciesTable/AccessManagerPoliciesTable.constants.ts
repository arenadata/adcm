import { TableColumn } from '@uikit';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'policyName',
    isSortable: true,
  },
  {
    label: 'Description',
    name: 'policyDescription',
  },
  {
    label: 'Role',
    name: 'policyRole',
  },
  {
    label: 'Group',
    name: 'policyGroup',
  },
  {
    label: 'Actions',
    name: 'policyActions',
    headerAlign: 'center',
    width: '100px',
  },
];
