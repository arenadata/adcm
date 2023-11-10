import { TableColumn, BaseStatus } from '@uikit';
import { AdcmBundleSignatureStatus } from '@models/adcm/bundle';

export const columns: TableColumn[] = [
  {
    isCheckAll: true,
    name: 'checkAll',
  },
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
    label: 'Edition',
    name: 'edition',
  },
  {
    label: 'Date upload',
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
    label: 'Actions',
    name: 'actions',
    headerAlign: 'center',
    width: '100px',
  },
];

export const bundleSignatureStatusesMap: { [key in AdcmBundleSignatureStatus]: BaseStatus } = {
  [AdcmBundleSignatureStatus.Valid]: 'done',
  [AdcmBundleSignatureStatus.Invalid]: 'failed',
  [AdcmBundleSignatureStatus.Absent]: 'created',
};
