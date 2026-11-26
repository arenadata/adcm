import { useMemo, useCallback } from 'react';
import { useDispatch, useForm, useStore } from '@hooks';
import { addClusterHostsWithUpdate, loadHostCandidates } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import { useParams } from 'react-router-dom';

interface CreateClusterHostsPayload {
  selectedHostIds: Set<number>;
}

const createInitialFormData = (): CreateClusterHostsPayload => ({
  selectedHostIds: new Set(),
});

export const useCreateClusterHostsForm = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const hostCandidates = useStore(({ adcm }) => adcm.clusterHostsActions.relatedData.hostCandidates);

  const hostCandidatesOptions = useMemo(() => {
    return hostCandidates?.map(({ name, id }) => ({ value: id, label: name }));
  }, [hostCandidates]);

  const { formData, setFormData, handleChangeFormData } =
    useForm<CreateClusterHostsPayload>(createInitialFormData());

  const isValid = useMemo(() => {
    return formData.selectedHostIds.size > 0;
  }, [formData.selectedHostIds]);

  const resetForm = useCallback(() => {
    setFormData(createInitialFormData());
  }, [setFormData]);

  const submit = useCallback(() => {
    const { selectedHostIds } = formData;
    if (selectedHostIds.size > 0) {
      dispatch(
        addClusterHostsWithUpdate({
          selectedHostIds: [...selectedHostIds],
          clusterId,
        }),
      );
    }
  }, [formData, dispatch, clusterId]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadHostCandidates(clusterId));
  }, [dispatch]);

  const handleFormDataChange = (changes: Partial<CreateClusterHostsPayload>) => {
    handleChangeFormData(changes);
  };

  return {
    isValid,
    formData,
    resetForm,
    submit,
    onChangeFormData: handleFormDataChange,
    loadRelatedData,
    relatedData: {
      hostCandidatesOptions,
    },
  };
};
