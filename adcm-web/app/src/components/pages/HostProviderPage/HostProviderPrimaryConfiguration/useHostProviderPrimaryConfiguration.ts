import { useDispatch, useStore } from '@hooks';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useHostProviderPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);
  const accessConfigCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessConfigCheckStatus);

  useEffect(() => {
    if (hostProvider?.id) {
      // load all configurations for current HostProvider
      dispatch(getConfigurationsVersions({ entityType: 'host-provider', args: { hostProviderId: hostProvider.id } }));
    }

    return () => {
      dispatch(cleanup());
    };
  }, [hostProvider?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (hostProvider?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'host-provider',
          args: { hostProviderId: hostProvider.id, configId: selectedConfigId },
        }),
      );
    }
  }, [dispatch, hostProvider?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (hostProvider?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'host-provider',
            args: {
              configurationData,
              attributes,
              hostProviderId: hostProvider.id,
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
    accessCheckStatus,
    accessConfigCheckStatus,
  };
};
