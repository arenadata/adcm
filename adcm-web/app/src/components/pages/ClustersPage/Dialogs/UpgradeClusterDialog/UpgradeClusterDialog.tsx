import { useMemo } from 'react';
import { Checkbox, Dialog, FormFieldsContainer, FormField, Select } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import TextFormField from '@commonComponents/Forms/TextFormField/TextFormField';
import { AdcmClusterUpgrade } from '@models/adcm';
import { useUpgradeClusterDialog } from './useUpgradeClusterDialog';

const UpgradeClusterDialog = () => {
  const {
    isOpen,
    cluster,
    relatedData,
    formData,
    isValid,
    onUpgrade,
    onClose,
    onChangeFormData,
    onLoadUpgradeActionDetails,
  } = useUpgradeClusterDialog();

  const upgradesOptions = useMemo(
    () => getOptionsFromArray(relatedData.upgrades, (x) => x.displayName),
    [relatedData.upgrades],
  );

  const handleUpgradeChange = (value: AdcmClusterUpgrade | null) => {
    onChangeFormData({ upgrade: value });
    if (value) {
      onLoadUpgradeActionDetails(value?.id);
    }
  };

  const handleTermsOfAgreementChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ isUserAcceptedLicense: event.target.checked });
  };

  const dialogControls = (
    <CustomDialogControls
      actionButtonLabel="Upgrade"
      onCancel={onClose}
      onAction={onUpgrade}
      isActionDisabled={!isValid}
    >
      <Checkbox
        label="I accept Terms of Agreement"
        checked={formData.isUserAcceptedLicense}
        onChange={handleTermsOfAgreementChange}
      />
    </CustomDialogControls>
  );

  return (
    <Dialog title="Upgrade cluster" isOpen={isOpen} onOpenChange={onClose} dialogControls={dialogControls}>
      <FormFieldsContainer>
        <FormField label="Cluster">
          <TextFormField>{cluster?.name}</TextFormField>
        </FormField>
        <FormField label="Upgrade to version">
          <Select
            placeholder="Select available"
            value={formData.upgrade}
            onChange={handleUpgradeChange}
            options={upgradesOptions}
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default UpgradeClusterDialog;
