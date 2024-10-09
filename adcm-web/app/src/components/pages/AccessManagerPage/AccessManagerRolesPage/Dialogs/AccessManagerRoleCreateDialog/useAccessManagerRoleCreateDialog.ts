import { useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmCreateRolePayload } from '@models/adcm';
import { createRole, closeCreateDialog } from '@store/adcm/roles/rolesActionsSlice';
import { isNameUniq, required } from '@utils/validationsUtils';

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
  const isOpen = useStore((s) => s.adcm.rolesActions.createDialog.isOpen);
  const roles = useStore((s) => s.adcm.roles.roles);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<AdcmCreateRoleFormData>(initialFormData);

  useEffect(() => {
    if (!isOpen) {
      setFormData(initialFormData);
    }
  }, [isOpen, setFormData]);

  useEffect(() => {
    setErrors({
      displayName:
        (required(formData.displayName) ? undefined : 'Role name field is required') ||
        (isNameUniq(
          formData.displayName,
          roles.map((role) => ({ ...role, name: role.displayName })),
        )
          ? undefined
          : 'Role with the same name already exists'),
      children: formData.children.size > 0 ? undefined : 'Can not create Role without permission',
    });
  }, [formData, roles, setErrors]);

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
