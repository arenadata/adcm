import { useEffect, useCallback } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { isHostNameValid, required } from '@utils/validationsUtils';
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

  const isNameUniq = useCallback(
    (name: string) => {
      return !hosts.find((host) => host.name === name);
    },
    [hosts],
  );

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
        (isNameUniq(formData.name) ? undefined : 'Enter unique host name'),
    });
  }, [formData, setErrors, isNameUniq]);

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
    isValid,
    formData,
    errors,
    onClose: handleClose,
    onRename: handleRename,
    onChangeFormData: handleChangeFormData,
  };
};
