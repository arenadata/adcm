import { DialogV2, FormField, FormFieldsContainer, Input } from '@uikit';
import { useUpdateClusterDialog } from './useUpdateClusterDialog';

const UpdateClusterDialog = () => {
  const { hasClusterForUpdate, formData, isValid, onRename, onClose, onChangeFormData, errors } =
    useUpdateClusterDialog();

  if (!hasClusterForUpdate) return null;

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  return (
    <DialogV2
      title="Rename cluster"
      onCancel={onClose}
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
    </DialogV2>
  );
};

export default UpdateClusterDialog;
