import { useCallback, useEffect, useRef, useState } from 'react';
import type { AdcmConfigShortView, AdcmConfiguration, ConfigurationData } from '@models/adcm';
import { useStore } from '@hooks';
import { mergeWithRawData, storeRawData } from './useConfigurations.utils';

const getDefaultConfigVersion = (configVersions: AdcmConfigShortView[]) =>
  configVersions.find(({ isCurrent }) => isCurrent)?.id ?? configVersions[0]?.id ?? null;

interface UseConfigurationProps {
  configVersions: AdcmConfigShortView[];
}

export const useConfigurations = ({ configVersions }: UseConfigurationProps) => {
  const [selectedConfigId, setSelectedConfigId] = useState<AdcmConfigShortView['id'] | null>(null);
  const [draftConfiguration, setDraftConfiguration] = useState<AdcmConfiguration | null>(null);
  const rawConfigDataRef = useRef<ConfigurationData>({});
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);

  useEffect(() => {
    // switch to default or draft configuration
    const newId = draftConfiguration === null ? getDefaultConfigVersion(configVersions) : 0;
    setSelectedConfigId(newId);
  }, [draftConfiguration, configVersions, setSelectedConfigId]);

  useEffect(() => {
    if (loadedConfiguration && draftConfiguration === null) {
      rawConfigDataRef.current = storeRawData({}, loadedConfiguration.configurationData, undefined);
    }
  }, [loadedConfiguration, draftConfiguration]);

  const setDraftConfigurationWithMerge = useCallback(
    (configuration: AdcmConfiguration | null) => {
      if (configuration === null) {
        setDraftConfiguration(null);
        rawConfigDataRef.current = {};
        return;
      }

      const { configurationData } = configuration;
      const currentDraftData = draftConfiguration?.configurationData;

      if (Object.keys(rawConfigDataRef.current).length === 0) {
        rawConfigDataRef.current = storeRawData({}, configurationData, undefined);
      }

      const draftData = mergeWithRawData(rawConfigDataRef.current, configurationData, currentDraftData);

      rawConfigDataRef.current = storeRawData(rawConfigDataRef.current, configurationData, currentDraftData);

      setDraftConfiguration({ ...configuration, configurationData: draftData });
    },
    [draftConfiguration],
  );

  const onReset = useCallback(() => {
    setDraftConfiguration(null);
    rawConfigDataRef.current = {};
  }, []);

  return {
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    setDraftConfiguration: setDraftConfigurationWithMerge,
    onReset,
  };
};
