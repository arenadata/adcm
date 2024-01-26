import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';

export const useSettingsConfiguration = () => {
  const dispatch = useDispatch();
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);

  useEffect(() => {
    dispatch(getConfigurationsVersions({ entityType: 'settings', args: {} }));

    return () => {
      dispatch(cleanup());
    };
  }, [dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (selectedConfigId) {
      dispatch(
        getConfiguration({
          entityType: 'settings',
          args: { configId: selectedConfigId },
        }),
      );
    }
  }, [dispatch, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'settings',
            args: {
              configurationData,
              attributes,
              description,
            },
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
