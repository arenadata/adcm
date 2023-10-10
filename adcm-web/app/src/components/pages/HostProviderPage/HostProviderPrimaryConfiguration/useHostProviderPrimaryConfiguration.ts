import { useDispatch, useStore } from '@hooks';
import {
  cleanupHostProviderConfiguration,
  createWithUpdateHostProviderConfigurations,
  getHostProviderConfiguration,
  getHostProviderConfigurationsVersions,
} from '@store/adcm/hostProvider/configuration/hostProviderConfigurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useHostProviderPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const configVersions = useStore(({ adcm }) => adcm.hostProviderConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.hostProviderConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.hostProviderConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.hostProviderConfiguration.isVersionsLoading);

  useEffect(() => {
    if (hostProvider) {
      // load all configurations for current HostProvider
      dispatch(getHostProviderConfigurationsVersions({ hostProviderId: hostProvider.id }));
    }

    return () => {
      dispatch(cleanupHostProviderConfiguration());
    };
  }, [hostProvider, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (hostProvider && selectedConfigId) {
      // load full config for selected configuration
      dispatch(getHostProviderConfiguration({ hostProviderId: hostProvider.id, configId: selectedConfigId }));
    }
  }, [dispatch, hostProvider, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (hostProvider?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateHostProviderConfigurations({
            configurationData,
            attributes,
            hostProviderId: hostProvider.id,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, hostProvider, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    hostProvider,
  };
};
