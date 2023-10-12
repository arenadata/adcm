import { useDispatch, useStore } from '@hooks';
import {
  cleanupHostsConfiguration,
  createWithUpdateHostsConfigurations,
  getHostsConfiguration,
  getHostsConfigurationsVersions,
} from '@store/adcm/host/configuration/hostsConfigurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations.ts';

export const useHostsPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const host = useStore(({ adcm }) => adcm.host.host);
  const configVersions = useStore(({ adcm }) => adcm.hostsConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.hostsConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.hostsConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.hostsConfiguration.isVersionsLoading);

  useEffect(() => {
    if (host) {
      // load all configurations for current Host
      dispatch(getHostsConfigurationsVersions(host.id));
    }

    return () => {
      dispatch(cleanupHostsConfiguration());
    };
  }, [host, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (host && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getHostsConfiguration({
          hostId: host.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, host, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (host?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateHostsConfigurations({
            configurationData,
            attributes,
            hostId: host.id,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, host, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    host,
  };
};
