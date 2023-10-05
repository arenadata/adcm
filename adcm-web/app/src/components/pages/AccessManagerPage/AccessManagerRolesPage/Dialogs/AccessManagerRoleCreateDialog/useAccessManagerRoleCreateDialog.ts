import { useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmCreateRolePayload } from '@models/adcm';
import { createRole, closeCreateDialog } from '@store/adcm/roles/rolesActionsSlice';
import { required } from '@utils/validationsUtils';

interface AdcmCreateRoleFormData extends Omit<AdcmCreateRolePayload, 'children'> {
  children: Set<number>;
}

const initialFormData: AdcmCreateRoleFormData = {
  displayName: '',
  description: '',
  children: new Set<number>(),
};

export const useAccessManagerRoleCreateDialog = () => {
  const dispatch = useDispatch();
  const isOpen = useStore((s) => s.adcm.rolesActions.isCreateDialogOpened);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<AdcmCreateRoleFormData>(initialFormData);

  useEffect(() => {
    if (!isOpen) {
      setFormData(initialFormData);
    }
  }, [isOpen, setFormData]);

  useEffect(() => {
    setErrors({
      displayName: required(formData.displayName) ? undefined : 'Username field is required',
      children: formData.children.size > 0 ? undefined : 'Can not create Role without permission',
    });
  }, [formData, setErrors]);

  const handleClose = () => {
    dispatch(closeCreateDialog());
  };

  const handleCreate = () => {
    dispatch(
      createRole({
        displayName: formData.displayName,
        description: formData.description,
        children: [...formData.children],
      }),
    );
  };

  return {
    isOpen,
    formData,
    isValid,
    errors,
    onClose: handleClose,
    onCreate: handleCreate,
    onChangeFormData: handleChangeFormData,
  };
};
