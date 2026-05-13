import type React from 'react';
import { DialogV2, FormField, FormFieldsContainer, MultilineInput } from '@uikit';
import {
  type EditDescriptionFormData,
  useEditActionHostGroupDescriptionDialog,
} from './useEditActionHostGroupDescriptionDialog';

export const EDIT_ACTION_HOST_GROUP_DESCRIPTION_TITLE = 'Edit action host group description';

export interface EditActionHostGroupDescription {
  isOpen: boolean;
  onEdit: (formData: EditDescriptionFormData) => void;
  onClose: () => void;
}

const EditDescriptionActionHostGroupDialog: React.FC<EditActionHostGroupDescription> = ({
  isOpen,
  onEdit,
  onClose,
}) => {
  const { formData, isValid, onChangeFormData, errors } = useEditActionHostGroupDescriptionDialog();

  if (!isOpen) return null;

  const handleAction = () => {
    onEdit(formData);
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  return (
    <DialogV2
      title={EDIT_ACTION_HOST_GROUP_DESCRIPTION_TITLE}
      onCancel={onClose}
      onAction={handleAction}
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

export default EditDescriptionActionHostGroupDialog;
