import { useMemo, useCallback, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { createHostDuplicate, loadClusters } from '@store/adcm/hosts/hostsActionsSlice';
import { isHostNameValid, required } from '@utils/validationsUtils';

interface CreateHostsFormData {
  name: string;
  clusterId: number | null;
}

const initialFormData: CreateHostsFormData = {
  name: '',
  clusterId: null,
};

export const useFormHostShareDialog = () => {
  const dispatch = useDispatch();

  const clusters = useStore(({ adcm }) => adcm.hostsActions.relatedData.clusters);
  const clustersOptions = useMemo(() => {
    return clusters.map(({ name, id }) => ({ value: id, label: name }));
  }, [clusters]);

  const { formData, setFormData, errors, setErrors, handleChangeFormData, isValid } =
    useForm<CreateHostsFormData>(initialFormData);

  const host = useStore(({ adcm }) => adcm.hostsActions.hostSharingDialog.host);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'The subhost name field is required') ||
        (isHostNameValid(formData.name) ? undefined : 'The subhost name field is incorrect'),
    });
  }, [formData, setErrors]);

  const reset = useCallback(() => {
    setFormData(initialFormData);
  }, [setFormData]);

  const submit = useCallback(() => {
    const { clusterId, name } = formData;
    const hostId = host?.id;

    if (hostId) {
      const payload = {
        clusterId,
        hostId,
        name,
      };

      dispatch(createHostDuplicate(payload));
    }
  }, [host, formData, dispatch]);

  const loadRelatedData = useCallback(() => {
    dispatch(loadClusters());
  }, [dispatch]);

  return {
    isValid,
    formData,
    reset,
    submit,
    onChangeFormData: handleChangeFormData,
    loadRelatedData,
    relatedData: {
      clustersOptions,
      host,
    },
    errors,
  };
};
