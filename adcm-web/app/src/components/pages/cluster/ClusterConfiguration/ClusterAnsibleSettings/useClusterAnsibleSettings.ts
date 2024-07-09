import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect, useState } from 'react';
import {
  cleanup,
  createWithUpdateAnsibleSettings,
  getConfiguration,
} from '@store/adcm/entityConfiguration/configurationSlice';
import type { AdcmConfiguration } from '@models/adcm';

export const useClusterAnsibleSettings = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);

  const [draftConfiguration, setDraftConfiguration] = useState<AdcmConfiguration | null>(null);

  const selectedConfiguration = draftConfiguration || loadedConfiguration;

  useEffect(() => {
    return () => {
      dispatch(cleanup());
    };
  }, [cluster, dispatch]);

  useEffect(() => {
    if (cluster) {
      dispatch(
        getConfiguration({
          entityType: 'cluster-ansible-settings',
          args: { clusterId: cluster.id },
        }),
      );
    }
  }, [dispatch, cluster]);

  const onReset = useCallback(() => {
    setDraftConfiguration(null);
  }, [setDraftConfiguration]);

  const onSave = useCallback(() => {
    if (cluster?.id) {
      dispatch(
        createWithUpdateAnsibleSettings({
          entityType: 'cluster-ansible-settings',
          args: {
            clusterId: cluster.id,
            config: { config: selectedConfiguration?.configurationData, adcmMeta: {} },
          },
        }),
      )
        .unwrap()
        .then(() => {
          onReset();
        });
    }
  }, [dispatch, cluster, selectedConfiguration, onReset]);

  return {
    setDraftConfiguration,
    draftConfiguration,
    onSave,
    onReset,
    selectedConfiguration,
    isConfigurationLoading,
    cluster,
    accessCheckStatus,
  };
};
