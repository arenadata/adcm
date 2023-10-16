import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanupSettings,
  createWithUpdateSettingsConfiguration,
  getSettingsConfiguration,
  getSettingsConfigurationVersions,
} from '@store/adcm/settings/configuration/settingsConfigurationSlice';

export const useSettingsConfiguration = () => {
  const dispatch = useDispatch();
  const configVersions = useStore(({ adcm }) => adcm.settingsConfigurations.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.settingsConfigurations.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.settingsConfigurations.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.settingsConfigurations.isVersionsLoading);

  useEffect(() => {
    dispatch(getSettingsConfigurationVersions());

    return () => {
      dispatch(cleanupSettings());
    };
  }, [dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (selectedConfigId) {
      dispatch(getSettingsConfiguration(selectedConfigId));
    }
  }, [dispatch, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateSettingsConfiguration({
            configurationData,
            attributes,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
  };
};
