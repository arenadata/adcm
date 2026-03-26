import { AdcmClustersWizardApi, AdcmServiceComponentsWizardApi, AdcmServicesWizardApi } from '@api';
import type { EntityWizardApi, WizardOwner } from '../types/wizardSlice.types';

export const entities: { [owner in WizardOwner]: EntityWizardApi } = {
  cluster: AdcmClustersWizardApi,
  service: AdcmServicesWizardApi,
  component: AdcmServiceComponentsWizardApi,
};
