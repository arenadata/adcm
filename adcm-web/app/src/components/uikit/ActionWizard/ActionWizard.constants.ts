import { AdcmJobStatus } from '@models/adcm';

export const terminalStatuses = new Set([
  AdcmJobStatus.Success,
  AdcmJobStatus.Failed,
  AdcmJobStatus.Locked,
  AdcmJobStatus.Aborted,
  AdcmJobStatus.Broken,
  AdcmJobStatus.Revoked,
]);

export const defaultWizardTitle = 'Manage install';
