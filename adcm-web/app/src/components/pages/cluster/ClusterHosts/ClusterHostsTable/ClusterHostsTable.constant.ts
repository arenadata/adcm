import { TableColumn } from '@uikit';
export { hostStatusesMap } from '@pages/HostsPage/HostsTable/HostsTable.constants';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: true,
  },
  {
    label: 'Hostprovider',
    name: 'hostprovider',
  },
  {
    label: 'Components',
    name: 'components',
  },
  {
    label: 'Concerns',
    name: 'concerns',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];
