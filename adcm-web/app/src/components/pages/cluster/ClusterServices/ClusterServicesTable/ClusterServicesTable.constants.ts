import { TableColumn, BaseStatus } from '@uikit';
import { AdcmServiceStatus } from '@models/adcm';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'displayName',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
  },
  {
    label: 'State',
    name: 'state',
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

export const servicesStatusesMap: { [key in AdcmServiceStatus]: BaseStatus } = {
  [AdcmServiceStatus.Up]: 'done',
  [AdcmServiceStatus.Down]: 'unknown',
};
