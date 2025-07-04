import type React from 'react';
import { useEffect } from 'react';
import { DialogV2, FormField, FormFieldsContainer, Input } from '@uikit';
import type { AdcmClusterConfigGroupCreateData } from '@api/adcm/clusterGroupConfig';
import { useForm } from '@hooks';
import { required } from '@utils/validationsUtils';
import s from './ConfigGroupCreateDialog.module.scss';

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

  if (!isOpen) return null;

  return (
    <DialogV2
      isActionDisabled={!isValid || isCreating}
      title="Create configuration group"
      actionButtonLabel="Next"
      onCancel={onClose}
      onAction={handleSubmit}
      className={s.configGroupCreateDialog}
    >
      <FormFieldsContainer>
        <FormField label="Configuration group name" error={errors.name}>
          <Input value={formData.name} onChange={handleChangeName} />
        </FormField>
        <FormField label="Description">
          <Input value={formData.description} onChange={handleChangeDescription} />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default ConfigGroupCreateDialog;
