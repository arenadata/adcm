import { useCallback, useEffect, useMemo } from 'react';
import { useForm } from '@hooks';
import { AdcmActionHostGroup } from '@models/adcm';
import { required } from '@utils/validationsUtils';

export type AdcmActionHostGroupFormData = Omit<AdcmActionHostGroup, 'id' | 'hosts'> & {
  hosts: Set<number>;
};

const emptyFormData: AdcmActionHostGroupFormData = {
  name: '',
  description: '',
  hosts: new Set(),
};

export const useActionHostGroupDialogForm = (actionHostGroup?: AdcmActionHostGroup) => {
  const initialFormData = useMemo(() => {
    return actionHostGroup
      ? {
          name: actionHostGroup.name,
          description: actionHostGroup.description,
          hosts: new Set(actionHostGroup.hosts.map((host) => host.id)),
        }
      : emptyFormData;
  }, [actionHostGroup]);

  const { setFormData, formData, handleChangeFormData, errors, setErrors, isValid } =
    useForm<AdcmActionHostGroupFormData>(initialFormData);

  useEffect(() => {
    setErrors({
      name: required(formData.name) ? undefined : 'Action host group name field is required',
    });
  }, [formData, setErrors]);

  const resetFormData = useCallback(() => {
    setFormData(initialFormData);
  }, [initialFormData, setFormData]);

  return {
    formData,
    isValid,
    errors,
    onChangeFormData: handleChangeFormData,
    resetFormData,
  };
};
