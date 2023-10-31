import { Dialog, FormField, FormFieldsContainer, Input } from '@uikit';
import { useUpdateHostDialog } from './useUpdateHostDialog';

const RenameHostDialog = () => {
  const { isOpen, formData, isValid, onRename, onClose, onChangeFormData, errors } = useUpdateHostDialog();

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  return (
    <Dialog
      title="Rename host"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onRename}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Host name" error={errors.name}>
          <Input value={formData.name} type="text" onChange={handleNameChange} placeholder="Enter unique host name" />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default RenameHostDialog;
