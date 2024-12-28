import { useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import type { AdcmUpdateRolePayload } from '@models/adcm';
import { updateRole, closeUpdateDialog, loadRelatedData } from '@store/adcm/roles/rolesActionsSlice';
import { isNameUniq, required } from '@utils/validationsUtils';

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
  const roles = useStore((s) => s.adcm.roles.roles);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<AdcmUpdateRoleFormData>(initialFormData);

  useEffect(() => {
    if (isOpen) {
      dispatch(loadRelatedData());
    } else {
      setFormData(initialFormData);
    }
  }, [isOpen, dispatch, setFormData]);

  useEffect(() => {
    setErrors({
      displayName:
        (required(formData.displayName) ? undefined : 'Role name field is required') ||
        (isNameUniq(
          formData.displayName,
          roles.filter(({ id }) => role?.id !== id).map((role) => ({ ...role, name: role.displayName })),
        )
          ? undefined
          : 'Role with the same name already exists'),
      children: formData.children.size > 0 ? undefined : 'Can not create Role without permission',
    });
  }, [formData, roles, role, setErrors]);

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
    dispatch(closeUpdateDialog());
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
