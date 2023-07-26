import { useMemo } from 'react';
import { Dialog, FormFieldsContainer, FormField, Input, Select } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import { AdcmPrototypeVersions, AdcmPrototypeVersion } from '@models/adcm';
import { useCreateHostProviderDialog } from './useCreateHostProviderDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';

const CreateHostProviderDialog = () => {
  const { isOpen, relatedData, formData, isValid, onCreate, onClose, onChangeFormData } = useCreateHostProviderDialog();

  const prototypeOptions = useMemo(
    () => getOptionsFromArray(relatedData.prototypeVersions, (x) => x.name),
    [relatedData.prototypeVersions],
  );

  const prototypeVersionsOptions = useMemo(
    () => (formData.prototype ? getOptionsFromArray(formData.prototype.versions, (x) => x.version) : []),
    [formData.prototype],
  );

  const handlePrototypeChange = (value: AdcmPrototypeVersions | null) => {
    onChangeFormData({ prototype: value });
  };

  const handlePrototypeVersionChange = (value: AdcmPrototypeVersion | null) => {
    if (value) {
      onChangeFormData({ prototypeVersion: value });
    }
  };

  const handleHostProviderNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const dialogControls = (
    <CustomDialogControls
      actionButtonLabel="Create"
      onCancel={onClose}
      onAction={onCreate}
      isActionDisabled={!isValid}
    />
  );

  return (
    <Dialog title="Create hostprovider" isOpen={isOpen} onOpenChange={onClose} dialogControls={dialogControls}>
      <FormFieldsContainer>
        <FormField label="Type">
          <Select
            placeholder="Select pre-downloaded bundle"
            value={formData.prototype}
            onChange={handlePrototypeChange}
            options={prototypeOptions}
          />
        </FormField>
        <FormField label="Version">
          <Select
            placeholder="Select available"
            disabled={formData.prototype === null}
            value={formData.prototypeVersion}
            onChange={handlePrototypeVersionChange}
            options={prototypeVersionsOptions}
          />
        </FormField>
        <FormField label="Name">
          <Input
            value={formData.name}
            type="text"
            onChange={handleHostProviderNameChange}
            placeholder="Enter unique cluster name"
          />
        </FormField>
        <FormField label="Description">
          <Input
            value={formData.description}
            type="text"
            onChange={handleDescriptionChange}
            placeholder="Description"
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default CreateHostProviderDialog;
