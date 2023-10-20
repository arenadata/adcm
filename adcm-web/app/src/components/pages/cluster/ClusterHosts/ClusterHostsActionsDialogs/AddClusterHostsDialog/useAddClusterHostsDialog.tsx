import { useState, useMemo, useCallback } from 'react';
import { useStore, useDispatch } from '@hooks';
import { addClusterHostsWithUpdate, loadHosts } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import { useParams } from 'react-router-dom';
import { AddClusterHostsPayload } from '@models/adcm';

interface CreateClusterHostsPayload extends Omit<AddClusterHostsPayload, 'clusterId'> {
  selectedHostIds: number[];
}

const initialFormData: CreateClusterHostsPayload = {
  selectedHostIds: [],
};

export const useCreateClusterHostsForm = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const hosts = useStore(({ adcm }) => adcm.clusterHostsActions.relatedData.hosts);

  const hostsOptions = useMemo(() => {
    return hosts.filter((host) => !host.cluster).map(({ name, id }) => ({ value: id, label: name }));
  }, [hosts]);

  const [formData, setFormData] = useState<CreateClusterHostsPayload>(initialFormData);

  const isValid = useMemo(() => {
    const { selectedHostIds } = formData;
    return selectedHostIds.length > 0;
  }, [formData]);

  const resetForm = useCallback(() => {
    setFormData(initialFormData);
  }, []);

  const submit = useCallback(() => {
    const { selectedHostIds } = formData;
    if (selectedHostIds.length > 0) {
      dispatch(
        addClusterHostsWithUpdate({
          selectedHostIds,
          clusterId,
        }),
      );
    }
  }, [formData, dispatch, clusterId]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadHosts());
  }, [dispatch]);

  const handleChangeFormData = (changes: Partial<CreateClusterHostsPayload>) => {
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
