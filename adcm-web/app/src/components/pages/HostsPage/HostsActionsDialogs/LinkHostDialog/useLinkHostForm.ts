import { useCallback, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { linkHost, loadClusters } from '@store/adcm/hosts/hostsActionsSlice';

interface LinkHostFormData {
  hostId: number | null;
  clusterId: number | null;
}

const initialFormData: LinkHostFormData = {
  hostId: null,
  clusterId: null,
};

export const useLinkHostForm = () => {
  const dispatch = useDispatch();

  const clusters = useStore(({ adcm }) => adcm.hostsActions.relatedData.clusters);
  const clustersOptions = useMemo(() => {
    return clusters.map(({ name, id }) => ({ value: id, label: name }));
  }, [clusters]);

  const relatedData = useMemo(
    () => ({
      clustersOptions,
    }),
    [clustersOptions],
  );

  const [formData, setFormData] = useState<LinkHostFormData>(initialFormData);

  const isValid = useMemo(() => {
    return !!(formData.hostId && formData.clusterId);
  }, [formData]);

  const reset = useCallback(() => {
    setFormData(initialFormData);
  }, []);

  const submit = useCallback(() => {
    const { clusterId, hostId } = formData;
    if (clusterId && hostId) {
      dispatch(linkHost({ clusterId, hostId }));
    }
  }, [formData, dispatch]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadClusters());
  }, [dispatch]);

  const handleChangeFormData = useCallback((changes: Partial<LinkHostFormData>) => {
    // use prev we can not set formData in dependency array
    setFormData((prev) => ({
      ...prev,
      ...changes,
    }));
  }, []);

  return {
    isValid,
    formData,
    reset,
    submit,
    onChangeFormData: handleChangeFormData,
    loadRelatedData,
    relatedData,
  };
};
