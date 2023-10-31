import { useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmUpdateRolePayload } from '@models/adcm';
import { updateRole, closeEditDialog } from '@store/adcm/roles/rolesActionsSlice';
import { required } from '@utils/validationsUtils';

interface AdcmUpdateRoleFormData extends Omit<AdcmUpdateRolePayload, 'children'> {
  children: Set<number>;
}

const initialFormData: AdcmUpdateRoleFormData = {
  displayName: '',
  description: '',
  children: new Set<number>(),
};

export const useAccessManagerRoleUpdateDialog = () => {
  const dispatch = useDispatch();
  const role = useStore((s) => s.adcm.rolesActions.updateDialog.role);
  const isOpen = !!role;

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<AdcmUpdateRoleFormData>(initialFormData);

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

  useEffect(() => {
    if (role) {
      setFormData({
        ...initialFormData,
        displayName: role.displayName,
        description: role.description,
        children: new Set<number>(role.children?.map((child) => child.id)),
      });
    }
  }, [role, setFormData]);

  const handleClose = () => {
    dispatch(closeEditDialog());
  };

  const handleUpdate = () => {
    if (role) {
      dispatch(
        updateRole({
          id: role?.id,
          data: {
            displayName: formData.displayName,
            description: formData.description,
            children: [...formData.children],
          },
        }),
      );
    }
  };

  return {
    isOpen,
    formData,
    isValid,
    errors,
    onClose: handleClose,
    onUpdate: handleUpdate,
    onChangeFormData: handleChangeFormData,
  };
};
