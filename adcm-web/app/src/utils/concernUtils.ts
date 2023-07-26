import { AdcmConcernReason } from '@models/adcm/concern';

export const formatConcernMessage = (reason: AdcmConcernReason | undefined): string => {
  if (!reason) {
    return '';
  }

  return reason.message
    .replace('${source}', reason.placeholder.source.name)
    .replace('${target}', reason.placeholder.target?.name || '');
};
