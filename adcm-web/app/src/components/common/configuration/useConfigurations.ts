import { useCallback, useEffect, useState } from 'react';
import type { AdcmConfigShortView, AdcmConfiguration } from '@models/adcm';

const getDefaultConfigVersion = (configVersions: AdcmConfigShortView[]) =>
  configVersions.find(({ isCurrent }) => isCurrent)?.id ?? configVersions[0]?.id ?? null;

interface UseConfigurationProps {
  configVersions: AdcmConfigShortView[];
}

export const useConfigurations = ({ configVersions }: UseConfigurationProps) => {
  const [selectedConfigId, setSelectedConfigId] = useState<AdcmConfigShortView['id'] | null>(null);
  const [draftConfiguration, setDraftConfiguration] = useState<AdcmConfiguration | null>(null);

  useEffect(() => {
    // switch to default or draft configuration
    const newId = draftConfiguration === null ? getDefaultConfigVersion(configVersions) : 0;
    setSelectedConfigId(newId);
  }, [draftConfiguration, configVersions, setSelectedConfigId]);

  const onReset = useCallback(() => {
    setDraftConfiguration(null);
  }, [setDraftConfiguration]);

  return {
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    setDraftConfiguration,
    onReset,
  };
};
