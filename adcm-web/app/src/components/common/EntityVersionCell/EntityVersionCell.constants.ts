import { AdcmBundleSignatureStatus, AdcmContractVersionStatus } from '@models/adcm';
import type { BaseStatus } from '@uikit';
import { contractVersionBadgeStatuses } from '@utils/contractVersionUtils';

export const entitySignatureStatusesMap: { [key in AdcmBundleSignatureStatus]: BaseStatus } = {
  [AdcmBundleSignatureStatus.Valid]: 'done',
  [AdcmBundleSignatureStatus.Invalid]: 'failed',
  [AdcmBundleSignatureStatus.Absent]: 'created',
};

export const entityContractVersionTooltips: Partial<Record<AdcmContractVersionStatus, string>> = {
  [AdcmContractVersionStatus.Unsupported]: 'Not supported',
  [AdcmContractVersionStatus.Deprecated]: 'Deprecated',
};

export { contractVersionBadgeStatuses as entityContractVersionBadgeStatuses };
