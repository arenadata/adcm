import { useMemo } from 'react';
import { Checkbox, Dialog, FormField, FormFieldsContainer, Input, Select } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import { AdcmPrototypeVersion, AdcmPrototypeVersions, AdcmLicenseStatus } from '@models/adcm';
import { useCreateClusterDialog } from './useCreateClusterDialog';

const CreateClusterDialog = () => {
  const { isOpen, relatedData, formData, isValid, onCreate, onClose, onChangeFormData } = useCreateClusterDialog();

  const productsOptions = useMemo(
    () => getOptionsFromArray(relatedData.prototypeVersions, (x) => x.name),
    [relatedData.prototypeVersions],
  );

  const productVersionsOptions = useMemo(
    () => (formData.product ? getOptionsFromArray(formData.product.versions, (x) => x.version) : []),
    [formData.product],
  );

  const handleProductChange = (value: AdcmPrototypeVersions | null) => {
    onChangeFormData({ product: value });
  };

  const handleProductVersionChange = (value: AdcmPrototypeVersion | null) => {
    if (value) {
      onChangeFormData({
        productVersion: value,
        isUserAcceptedLicense: value.licenseStatus === AdcmLicenseStatus.Accepted,
      });
    }
  };

  const handleClusterNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
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
      {formData.productVersion && formData.productVersion.licenseStatus !== AdcmLicenseStatus.Absent && (
        <Checkbox
          label="I accept Terms of Agreement"
          checked={formData.isUserAcceptedLicense}
          disabled={formData.productVersion?.licenseStatus === AdcmLicenseStatus.Accepted}
          onChange={handleTermsOfAgreementChange}
        />
      )}
    </CustomDialogControls>
  );

  return (
    <Dialog title="Create cluster" isOpen={isOpen} onOpenChange={onClose} dialogControls={dialogControls}>
      <FormFieldsContainer>
        <FormField label="Product">
          <Select
            placeholder="Select pre-downloaded bundle"
            value={formData.product}
            onChange={handleProductChange}
            options={productsOptions}
          />
        </FormField>
        <FormField label="Product version">
          <Select
            placeholder="Select available"
            disabled={formData.product === null}
            value={formData.productVersion}
            onChange={handleProductVersionChange}
            options={productVersionsOptions}
          />
        </FormField>
        <FormField label="Cluster name">
          <Input
            value={formData.name}
            type="text"
            onChange={handleClusterNameChange}
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

export default CreateClusterDialog;
