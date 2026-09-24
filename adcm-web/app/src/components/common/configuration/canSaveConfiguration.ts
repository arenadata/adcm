import type { AdcmConfigShortView } from '@models/adcm';

export const canSaveConfiguration = (
  selectedConfigId: AdcmConfigShortView['id'] | null,
  configVersions: Pick<AdcmConfigShortView, 'id' | 'isCurrent'>[],
): boolean => {
  if (selectedConfigId === null) {
    return false;
  }

  const currentConfigId = configVersions.find(({ isCurrent }) => isCurrent)?.id;

  return selectedConfigId !== currentConfigId;
};
