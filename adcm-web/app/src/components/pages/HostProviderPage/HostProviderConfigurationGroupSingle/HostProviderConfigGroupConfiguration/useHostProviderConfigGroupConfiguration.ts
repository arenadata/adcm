import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useHostProviderConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const hostProviderConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroup.hostProviderConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);

  useEffect(() => {
    if (hostProvider?.id && hostProviderConfigGroup?.id) {
      // load all configurations for current HostProvider
      dispatch(
        getConfigurationsVersions({
          entityType: 'host-provider-config-group',
          args: {
            hostProviderId: hostProvider.id,
            configGroupId: hostProviderConfigGroup.id,
          },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [hostProvider?.id, hostProviderConfigGroup?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (hostProvider?.id && hostProviderConfigGroup?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'host-provider-config-group',
          args: {
            hostProviderId: hostProvider.id,
            configGroupId: hostProviderConfigGroup.id,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [dispatch, hostProvider?.id, hostProviderConfigGroup?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (hostProvider?.id && hostProviderConfigGroup?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'host-provider-config-group',
            args: {
              configurationData,
              attributes,
              hostProviderId: hostProvider.id,
              configGroupId: hostProviderConfigGroup.id,
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
