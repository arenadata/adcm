import { useState, useMemo, useCallback } from 'react';
import { useStore, useDispatch } from '@hooks';
import { addClusterHosts, loadHosts } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import { useParams } from 'react-router-dom';

interface CreateClusterHostsFormData {
  hostIds: number[];
  clusterId: number | null;
}

const initialFormData: CreateClusterHostsFormData = {
  hostIds: [],
  clusterId: null,
};

export const useCreateClusterHostsForm = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const hosts = useStore(({ adcm }) => adcm.clusterHostsActions.relatedData.hosts);

  const hostsOptions = useMemo(() => {
    return hosts.filter((host) => !host.cluster).map(({ name, id }) => ({ value: id, label: name }));
  }, [hosts]);

  const [formData, setFormData] = useState<CreateClusterHostsFormData>(initialFormData);

  const isValid = useMemo(() => {
    const { hostIds } = formData;
    return hostIds.length > 0;
  }, [formData]);

  const resetForm = useCallback(() => {
    setFormData(initialFormData);
  }, []);

  const submit = useCallback(() => {
    const { hostIds } = formData;
    if (hostIds.length > 0) {
      dispatch(
        addClusterHosts({
          hostIds,
          clusterId: clusterId ?? undefined,
        }),
      );
    }
  }, [formData, dispatch]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadHosts());
  }, [dispatch]);

  const handleChangeFormData = (changes: Partial<CreateClusterHostsFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isValid,
    formData,
    resetForm,
    submit,
    onChangeFormData: handleChangeFormData,
    loadRelatedData,
    relatedData: {
      hostsOptions,
    },
  };
};
