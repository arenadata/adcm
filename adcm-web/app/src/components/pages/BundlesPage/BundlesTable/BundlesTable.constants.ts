import { TableColumn, BaseStatus } from '@uikit';
import { AdcmBundleSignatureStatus } from '@models/adcm/bundle';

export const columns: TableColumn[] = [
  {
    isCheckAll: true,
    name: 'checkAll',
  },
  {
    label: 'Name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'Version',
    name: 'version',
    isSortable: false,
  },
  {
    label: 'Edition',
    name: 'edition',
    isSortable: false,
  },
  {
    label: 'Date upload',
    name: 'uploadTime',
    isSortable: false,
  },
  {
    label: 'Signature',
    name: 'signatureStatus',
    isSortable: false,
  },
  {
    label: 'Actions',
    name: 'actions',
    isSortable: false,
    headerAlign: 'center',
    width: '100px',
  },
];

export const bundleSignatureStatusesMap: { [key in AdcmBundleSignatureStatus]: BaseStatus } = {
  [AdcmBundleSignatureStatus.Verified]: 'done',
  [AdcmBundleSignatureStatus.NotVerified]: 'failed',
};
