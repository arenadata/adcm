import type { TableColumn, BaseStatus } from '@uikit';
import type { BadgeStatus } from '@uikit/Badge/Badge.types';
import { AdcmBundleSignatureStatus, AdcmContractVersionStatus } from '@models/adcm/bundle';

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

export const bundleSignatureStatusesMap: { [key in AdcmBundleSignatureStatus]: BaseStatus } = {
  [AdcmBundleSignatureStatus.Valid]: 'done',
  [AdcmBundleSignatureStatus.Invalid]: 'failed',
  [AdcmBundleSignatureStatus.Absent]: 'created',
};

export const bundleContractVersionTooltips: Partial<Record<AdcmContractVersionStatus, string>> = {
  [AdcmContractVersionStatus.Unsupported]: 'Not supported',
  [AdcmContractVersionStatus.Deprecated]: 'Deprecated',
};

export const bundleContractVersionBadgeStatuses: Record<AdcmContractVersionStatus, BadgeStatus> = {
  [AdcmContractVersionStatus.Unsupported]: 'danger',
  [AdcmContractVersionStatus.Deprecated]: 'warning',
  [AdcmContractVersionStatus.Supported]: 'info',
};
