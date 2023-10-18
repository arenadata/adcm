import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanupHostProviderConfigGroupConfiguration,
  createWithUpdateHostProviderConfigGroupConfigurations,
  getHostProviderConfigGroupConfiguration,
  getHostProviderConfigGroupConfigurationsVersions,
} from '@store/adcm/hostProvider/configurationGroupSingle/configuration/hostProviderConfigGroupConfigurationSlice';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useHostProviderConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const hostProviderConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroup.hostProviderConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.hostProviderConfigGroupConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.hostProviderConfigGroupConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(
    ({ adcm }) => adcm.hostProviderConfigGroupConfiguration.isConfigurationLoading,
  );
  const isVersionsLoading = useStore(({ adcm }) => adcm.hostProviderConfigGroupConfiguration.isVersionsLoading);

  useEffect(() => {
    if (hostProvider && hostProviderConfigGroup) {
      // load all configurations for current HostProvider
      dispatch(
        getHostProviderConfigGroupConfigurationsVersions({
          hostProviderId: hostProvider.id,
          configGroupId: hostProviderConfigGroup.id,
        }),
      );
    }

    return () => {
      dispatch(cleanupHostProviderConfigGroupConfiguration());
    };
  }, [hostProvider, hostProviderConfigGroup, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (hostProvider && hostProviderConfigGroup && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getHostProviderConfigGroupConfiguration({
          hostProviderId: hostProvider.id,
          configGroupId: hostProviderConfigGroup.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, hostProvider, hostProviderConfigGroup, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (hostProvider?.id && hostProviderConfigGroup?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateHostProviderConfigGroupConfigurations({
            configurationData,
            attributes,
            hostProviderId: hostProvider.id,
            configGroupId: hostProviderConfigGroup.id,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, hostProvider, hostProviderConfigGroup, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    hostProvider,
    hostProviderConfigGroup,
  };
};
