import { useMemo } from 'react';
import { Dialog, FormFieldsContainer, FormField, Input, Select, Checkbox } from '@uikit';
import { AdcmPrototypeVersions, AdcmPrototypeVersion, AdcmLicenseStatus } from '@models/adcm';
import { useCreateHostProviderDialog } from './useCreateHostProviderDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';

const CreateHostProviderDialog = () => {
  const { isOpen, relatedData, formData, isValid, errors, onCreate, onClose, onChangeFormData } =
    useCreateHostProviderDialog();

  const prototypeOptions = useMemo(
    () => relatedData.prototypeVersions.map((item) => ({ label: item.displayName, value: item })),
    [relatedData.prototypeVersions],
  );

  const prototypeVersionsOptions = useMemo(
    () => (formData.prototype ? formData.prototype.versions.map((item) => ({ label: item.version, value: item })) : []),
    [formData.prototype],
  );

  const handlePrototypeChange = (value: AdcmPrototypeVersions | null) => {
    onChangeFormData({ prototype: value });
  };

  const handlePrototypeVersionChange = (value: AdcmPrototypeVersion | null) => {
    if (value) {
      onChangeFormData({
        prototypeVersion: value,
        isUserAcceptedLicense: value.licenseStatus === AdcmLicenseStatus.Accepted,
      });
    }
  };

  const handleHostProviderNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleTermsOfAgreementChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ isUserAcceptedLicense: event.target.checked });
  };

  const dialogControls = (
    <CustomDialogControls actionButtonLabel="Create" onCancel={onClose} onAction={onCreate} isActionDisabled={!isValid}>
      {formData.prototypeVersion && formData.prototypeVersion.licenseStatus !== AdcmLicenseStatus.Absent && (
        <Checkbox
          label={
            <>
              I accept <LinkToLicenseText bundleId={formData.prototypeVersion.bundle.id} />
            </>
          }
          checked={formData.isUserAcceptedLicense}
          disabled={formData.prototypeVersion.licenseStatus === AdcmLicenseStatus.Accepted}
          onChange={handleTermsOfAgreementChange}
        />
      )}
    </CustomDialogControls>
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
        <FormField label="Name" error={errors.name}>
          <Input
            value={formData.name}
            type="text"
            onChange={handleHostProviderNameChange}
            placeholder="Enter unique hostprovider name"
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
