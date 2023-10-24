import { useEffect, useMemo } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { isHostNameValid, isNameUniq, required } from '@utils/validationsUtils';
import { closeUpdateDialog, updateHost } from '@store/adcm/hosts/hostsActionsSlice';

interface UpdateHostFormData {
  name: string;
}

const initialFormData: UpdateHostFormData = {
  name: '',
};

export const useUpdateHostDialog = () => {
  const dispatch = useDispatch();

  const { isValid, formData, setFormData, handleChangeFormData, errors, setErrors } =
    useForm<UpdateHostFormData>(initialFormData);

  const updatedHost = useStore((s) => s.adcm.hostsActions.updateDialog.host);
  const hosts = useStore((s) => s.adcm.hosts.hosts);

  const isNameChanged = useMemo(() => {
    return formData.name !== updatedHost?.name;
  }, [formData, updatedHost]);

  useEffect(() => {
    if (updatedHost) {
      const { name } = updatedHost;
      setFormData({ name });
    }
  }, [updatedHost, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Host name field is required') ||
        (isHostNameValid(formData.name) ? undefined : 'Host name field is incorrect') ||
        (isNameUniq(
          formData.name,
          hosts.filter(({ id }) => updatedHost?.id !== id),
        )
          ? undefined
          : 'Host with the same name already exists'),
    });
  }, [formData, updatedHost, hosts, setErrors]);

  const handleClose = () => {
    dispatch(closeUpdateDialog());
  };

  const handleRename = () => {
    if (updatedHost) {
      dispatch(
        updateHost({
          id: updatedHost.id,
          name: formData.name,
        }),
      );
    }
  };

  return {
    isOpen: !!updatedHost,
    isValid: isValid && isNameChanged,
    formData,
    errors,
    onClose: handleClose,
    onRename: handleRename,
    onChangeFormData: handleChangeFormData,
  };
};
