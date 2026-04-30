import { useEffect, useMemo } from 'react';
import { useStore, useForm } from '@hooks';

const DESCRIPTION_MAX_LENGTH = 256;

export interface EditDescriptionFormData {
  description: string;
}

const initialFormData: EditDescriptionFormData = {
  description: '',
};

export const useEditActionHostGroupDescriptionDialog = () => {
  const { isValid, formData, setFormData, handleChangeFormData, setErrors, errors } =
    useForm<EditDescriptionFormData>(initialFormData);

  const actionHostGroup = useStore((s) => s.adcm.actionHostGroupsActions.editDescriptionDialog.actionHostGroup);

  const currentDescription = actionHostGroup?.description ?? '';

  const isDescriptionChanged = useMemo(
    () => formData.description !== currentDescription,
    [formData.description, currentDescription],
  );

  useEffect(() => {
    if (actionHostGroup?.id) {
      setFormData({ description: currentDescription });
    }
  }, [actionHostGroup?.id, currentDescription, setFormData]);

  useEffect(() => {
    const error =
      formData.description.length <= DESCRIPTION_MAX_LENGTH
        ? undefined
        : `Description should be shorter or equal to ${DESCRIPTION_MAX_LENGTH}`;
    setErrors({ description: error });
  }, [formData.description, setErrors]);

  return {
    isValid: isValid && isDescriptionChanged,
    formData,
    errors,
    onChangeFormData: handleChangeFormData,
  };
};
