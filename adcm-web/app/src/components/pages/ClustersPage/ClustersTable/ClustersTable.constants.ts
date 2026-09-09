import type { TableColumn } from '@uikit';
import { clusterStatusesMap, clusterStatusLabels } from '@pages/ClustersPage/clusterStatusUtils';

export const columns: TableColumn[] = [
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'State',
    name: 'state',
    isSortable: false,
  },
  {
    label: 'Product',
    name: 'prototypeDisplayName',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
    isSortable: false,
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
    label: 'Operations',
    name: 'operations',
    isSortable: false,
    headerAlign: 'center',
    width: '100px',
  },
];

export { clusterStatusesMap, clusterStatusLabels };
