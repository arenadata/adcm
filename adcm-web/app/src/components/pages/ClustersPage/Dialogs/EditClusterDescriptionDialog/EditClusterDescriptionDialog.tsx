import { DialogV2, FormField, FormFieldsContainer, MultilineInput } from '@uikit';
import { useEditClusterDescriptionDialog } from './useEditClusterDescriptionDialog';
import type React from 'react';

const EditDescription = () => {
  const { hasClusterForUpdate, formData, isValid, onEditDescription, onClose, onChangeFormData, errors } =
    useEditClusterDescriptionDialog();

  if (!hasClusterForUpdate) return null;

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  return (
    <DialogV2
      title="Edit cluster description"
      onCancel={onClose}
      onAction={onEditDescription}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Cluster description" error={errors.description}>
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

export default EditDescription;
