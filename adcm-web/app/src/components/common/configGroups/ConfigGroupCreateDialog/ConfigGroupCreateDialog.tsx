import React, { useEffect } from 'react';
import { Dialog, FormField, FormFieldsContainer, Input } from '@uikit';
import { AdcmClusterConfigGroupCreateData } from '@api/adcm/clusterGroupConfig';
import { useForm } from '@hooks';
import { required } from '@utils/validationsUtils';

interface ConfigGroupCreateDialogProps {
  isCreating: boolean;
  isOpen: boolean;
  onSubmit: (data: AdcmClusterConfigGroupCreateData) => void;
  onClose: () => void;
}

const initialFormData = {
  name: '',
  description: '',
};

const ConfigGroupCreateDialog: React.FC<ConfigGroupCreateDialogProps> = ({ isCreating, isOpen, onClose, onSubmit }) => {
  const { formData, handleChangeFormData, setFormData, isValid, errors, setErrors } = useForm(initialFormData);

  useEffect(() => {
    if (!isOpen) {
      setFormData(initialFormData);
    }
  }, [isOpen, setFormData]);

  useEffect(() => {
    setErrors({
      name: required(formData.name) ? undefined : 'Name field is required',
    });
  }, [formData, setErrors]);

  const handleSubmit = () => {
    onSubmit(formData);
  };

  const handleChangeName = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleChangeFormData({ name: event.target.value });
  };
  const handleChangeDescription = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleChangeFormData({ description: event.target.value });
  };

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={onClose}
      isActionDisabled={!isValid || isCreating}
      title="Create configuration group"
      actionButtonLabel="Next"
      onCancel={onClose}
      onAction={handleSubmit}
    >
      <FormFieldsContainer>
        <FormField label="Configuration group name" error={errors.name}>
          <Input value={formData.name} onChange={handleChangeName} />
        </FormField>
        <FormField label="Description">
          <Input value={formData.description} onChange={handleChangeDescription} />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default ConfigGroupCreateDialog;
