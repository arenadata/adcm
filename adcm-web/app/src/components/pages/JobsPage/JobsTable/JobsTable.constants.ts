import { AdcmJobObjectType } from '@models/adcm';
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
  },
  {
    label: 'Status',
    name: 'status',
  },
  {
    label: 'Objects',
    name: 'objects',
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
    label: 'End time',
    name: 'endTime',
  },
  {
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];

export const linkByObjectTypeMap: { [key in AdcmJobObjectType]: string } = {
  [AdcmJobObjectType.Adcm]: '',
  [AdcmJobObjectType.Cluster]: 'clusters',
  [AdcmJobObjectType.Service]: 'services',
  [AdcmJobObjectType.Provider]: 'hostproviders',
  [AdcmJobObjectType.Host]: 'hosts',
  [AdcmJobObjectType.Component]: 'components',
};
