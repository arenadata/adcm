import { DialogV2, FormField, FormFieldsContainer, Input } from '@uikit';
import { useUpdateHostDialog } from './useUpdateHostDialog';

const RenameHostDialog = () => {
  const { hasHostForUpdate, formData, isValid, onRename, onClose, onChangeFormData, errors } = useUpdateHostDialog();

  if (!hasHostForUpdate) return null;

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  return (
    <DialogV2
      title="Rename host"
      onAction={onRename}
      onCancel={onClose}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Host name" error={errors.name}>
          <Input value={formData.name} type="text" onChange={handleNameChange} placeholder="Enter unique host name" />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default RenameHostDialog;
