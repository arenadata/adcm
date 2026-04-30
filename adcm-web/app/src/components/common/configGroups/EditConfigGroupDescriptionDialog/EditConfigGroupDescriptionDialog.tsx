import type React from 'react';
import { DialogV2, FormField, FormFieldsContainer, MultilineInput } from '@uikit';
import { useEditEntityDescriptionDialog } from './useEditEntityDescriptionDialog';

export const EDIT_CONFIG_GROUP_DESCRIPTION_TITLE = 'Edit configuration group description';

const EditConfigGroupDescriptionDialog = () => {
  const { isOpen, formData, isValid, onEditDescription, onClose, onChangeFormData, errors } =
    useEditEntityDescriptionDialog();

  if (!isOpen) return null;

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  return (
    <DialogV2
      title={EDIT_CONFIG_GROUP_DESCRIPTION_TITLE}
      onCancel={onClose}
      onAction={onEditDescription}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Description" error={errors.description}>
          <MultilineInput
            value={formData.description}
            onChange={handleDescriptionChange}
            placeholder="Enter description"
          />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default EditConfigGroupDescriptionDialog;
