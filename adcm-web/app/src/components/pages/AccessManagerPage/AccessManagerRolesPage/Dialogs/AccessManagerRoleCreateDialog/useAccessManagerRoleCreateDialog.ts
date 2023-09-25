import { useState } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmCreateRolePayload } from '@models/adcm';
import { createRole, closeCreateDialog } from '@store/adcm/roles/rolesActionsSlice';

const initialFormData: AdcmCreateRolePayload = {
  displayName: '',
  description: '',
  children: [],
};

export const useAccessManagerRoleCreateDialog = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<AdcmCreateRolePayload>(initialFormData);

  const {
    isCreateDialogOpened,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.rolesActions);

  const handleClose = () => {
    dispatch(closeCreateDialog());
  };

  const handleCreate = () => {
    dispatch(
      createRole({
        displayName: formData.displayName,
        description: formData.description,
        children: formData.children,
      }),
    );
  };

  const handleChangeFormData = (changes: Partial<AdcmCreateRolePayload>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isCreateDialogOpened,
    formData,
    relatedData,
    isRelatedDataLoaded,
    onClose: handleClose,
    onCreate: handleCreate,
    onChangeFormData: handleChangeFormData,
  };
};
