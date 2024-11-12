import type { AdcmConfigShortView } from '@models/adcm';

export enum ConfigVersionAction {
  Compare = 'compare',
  Delete = 'delete',
}

type DraftConfigurationId = 0;
type NotSelectedConfigurationId = null;

export interface ConfigVersion extends Omit<AdcmConfigShortView, 'id'> {
  id: AdcmConfigShortView['id'] | DraftConfigurationId | NotSelectedConfigurationId;
}

export type SelectVersionAction = { action: ConfigVersionAction; configId: ConfigVersion['id'] };
