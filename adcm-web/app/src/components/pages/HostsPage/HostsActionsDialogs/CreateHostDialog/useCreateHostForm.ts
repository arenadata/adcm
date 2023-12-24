import { useMemo, useCallback, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { createHostWithUpdate, loadClusters, loadHostProviders } from '@store/adcm/hosts/hostsActionsSlice';
import { isHostNameValid, isNameUniq, required } from '@utils/validationsUtils';

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

  const { formData, setFormData, errors, setErrors, handleChangeFormData, isValid } =
    useForm<CreateHostsFormData>(initialFormData);

  const hosts = useStore((s) => s.adcm.hosts.hosts);

  useEffect(() => {
    setErrors({
      hostproviderId: required(formData.hostproviderId) ? undefined : 'The host provider is required',
      hostName:
        (required(formData.hostName) ? undefined : 'The host name field is required') ||
        (isHostNameValid(formData.hostName) ? undefined : 'The host name field is incorrect') ||
        (isNameUniq(formData.hostName, hosts) ? undefined : 'Host with the same name already exists'),
    });
  }, [formData, hosts, setErrors]);

  const reset = useCallback(() => {
    setFormData(initialFormData);
  }, [setFormData]);

  const submit = useCallback(() => {
    const { clusterId, hostproviderId, hostName: name } = formData;
    if (hostproviderId && name) {
      dispatch(
        createHostWithUpdate({
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
    errors,
  };
};
