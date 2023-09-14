import { useMemo } from 'react';
import { Checkbox, Dialog, FormFieldsContainer, FormField, Select } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import TextFormField from '@commonComponents/Forms/TextFormField/TextFormField';
import { AdcmClusterUpgrade, AdcmLicenseStatus } from '@models/adcm';
import { useUpgradeClusterDialog } from './useUpgradeClusterDialog';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';

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
    onChangeFormData({
      upgrade: value,
      isUserAcceptedLicense: value?.licenseStatus === AdcmLicenseStatus.Accepted,
    });

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
      {relatedData?.upgradeActionDetails &&
        formData.upgrade &&
        formData.upgrade.licenseStatus !== AdcmLicenseStatus.Absent && (
          <Checkbox
            label={
              <>
                I accept <LinkToLicenseText bundleId={relatedData.upgradeActionDetails.bundle.id} />
              </>
            }
            checked={formData.isUserAcceptedLicense}
            disabled={formData.upgrade.licenseStatus === AdcmLicenseStatus.Accepted}
            onChange={handleTermsOfAgreementChange}
          />
        )}
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
