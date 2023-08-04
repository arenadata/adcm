import { useState, useMemo, useCallback } from 'react';
import { useStore, useDispatch } from '@hooks';
import { createHost, loadClusters, loadHostProviders } from '@store/adcm/hosts/hostsActionsSlice';

interface CreateHostsFormData {
  hostName: string;
  hostproviderId: number | null;
  clusterId: number | null;
}

const initialFormData: CreateHostsFormData = {
  hostName: '',
  hostproviderId: null,
  clusterId: null,
};

export const useCreateHostForm = () => {
  const dispatch = useDispatch();

  const hostProviders = useStore(({ adcm }) => adcm.hostsActions.relatedData.hostProviders);
  const hostProvidersOptions = useMemo(() => {
    return hostProviders.map(({ name, id }) => ({ value: id, label: name }));
  }, [hostProviders]);

  const clusters = useStore(({ adcm }) => adcm.hostsActions.relatedData.clusters);
  const clustersOptions = useMemo(() => {
    return clusters.map(({ name, id }) => ({ value: id, label: name }));
  }, [clusters]);

  const [formData, setFormData] = useState<CreateHostsFormData>(initialFormData);

  const isValid = useMemo(() => {
    const { hostproviderId, hostName } = formData;
    return !!(hostproviderId && hostName);
  }, [formData]);

  const reset = useCallback(() => {
    setFormData(initialFormData);
  }, []);

  const submit = useCallback(() => {
    const { clusterId, hostproviderId, hostName: name } = formData;
    if (hostproviderId && name) {
      dispatch(
        createHost({
          name,
          hostproviderId,
          clusterId: clusterId ?? undefined,
        }),
      );
    }
  }, [formData, dispatch]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadClusters());
    dispatch(loadHostProviders());
  }, [dispatch]);

  const handleChangeFormData = (changes: Partial<CreateHostsFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isValid,
    formData,
    reset,
    submit,
    onChangeFormData: handleChangeFormData,
    loadRelatedData,
    relatedData: {
      hostProvidersOptions,
      clustersOptions,
    },
  };
};
