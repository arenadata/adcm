import { Dialog, FormField, FormFieldsContainer, Input } from '@uikit';
import { useUpdateClusterDialog } from './useUpdateClusterDialog';

const UpdateClusterDialog = () => {
  const { isOpen, formData, isValid, onRename, onClose, onChangeFormData, errors } = useUpdateClusterDialog();

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  return (
    <Dialog
      title="Rename cluster"
      isOpen={isOpen}
      onOpenChange={onClose}
      onAction={onRename}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Cluster name" error={errors.name}>
          <Input
            value={formData.name}
            type="text"
            onChange={handleClusterNameChange}
            placeholder="Enter unique cluster name"
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default UpdateClusterDialog;
