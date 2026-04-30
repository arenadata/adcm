import { useEffect, useMemo } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import {
  closeEntityDescriptionDialog,
  editConfigGroupDescription,
} from '@store/adcm/entityDescriptionDialog/entityDescriptionDialogSlice';

const DESCRIPTION_MAX_LENGTH = 256;

interface EditDescriptionFormData {
  description: string;
}

const initialFormData: EditDescriptionFormData = {
  description: '',
};

export const useEditEntityDescriptionDialog = () => {
  const dispatch = useDispatch();

  const { isValid, formData, setFormData, handleChangeFormData, setErrors, errors } =
    useForm<EditDescriptionFormData>(initialFormData);

  const configGroup = useStore((s) => s.adcm.entityDescriptionDialog.configGroup);
  const entityType = useStore((s) => s.adcm.entityDescriptionDialog.entityType);
  const entityArgs = useStore((s) => s.adcm.entityDescriptionDialog.entityArgs);

  const currentDescription = configGroup?.description ?? '';

  const isDescriptionChanged = useMemo(
    () => formData.description !== currentDescription,
    [formData.description, currentDescription],
  );

  useEffect(() => {
    if (configGroup?.id) {
      setFormData({ description: currentDescription });
    }
  }, [configGroup?.id, currentDescription, setFormData]);

  useEffect(() => {
    const error =
      formData.description.length <= DESCRIPTION_MAX_LENGTH
        ? undefined
        : `Description should be shorter or equal to ${DESCRIPTION_MAX_LENGTH}`;
    setErrors({ description: error });
  }, [formData.description, setErrors]);

  const handleClose = () => {
    dispatch(closeEntityDescriptionDialog());
  };

  const handleEditDescription = () => {
    if (configGroup && entityType && entityArgs) {
      dispatch(
        editConfigGroupDescription({
          entityType,
          entityArgs,
          configGroupId: configGroup.id,
          description: formData.description,
        }),
      );
    }
  };

  return {
    isOpen: Boolean(configGroup),
    isValid: isValid && isDescriptionChanged,
    formData,
    errors,
    onClose: handleClose,
    onEditDescription: handleEditDescription,
    onChangeFormData: handleChangeFormData,
  };
};
