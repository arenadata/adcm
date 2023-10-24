import React from 'react';
import { useHostProviderUpgradeDialog } from '@pages/HostProvidersPage/Dialogs/HostProviderUpgradeDialog/useHostProviderUpgradeDialog';
import { UpgradeStepKey } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import { AdcmLicenseStatus } from '@models/adcm';
import { Checkbox, Dialog } from '@uikit';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';
import SelectUpgradeStep from './SelectUpgradeStep/SelectUpgradeStep';

const HostProviderUpgradeDialog: React.FC = () => {
  const {
    hostProvider,
    isValid,
    upgradeDetails,
    formData,
    handleChangeFormData,
    onSubmit,
    onNext,
    onClose,
    currentStep,
  } = useHostProviderUpgradeDialog();

  if (!hostProvider) return null;

  // for last step with set upgrade run config use DynamicActionDialog
  if (upgradeDetails && currentStep === UpgradeStepKey.UpgradeRunConfig) {
    return (
      <DynamicActionDialog
        // host provider actions can't set host mapping
        clusterId={0}
        actionDetails={upgradeDetails}
        onCancel={onClose}
        onSubmit={onSubmit}
      />
    );
  }

  const handleChangeAcceptedUpgradeLicense = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleChangeFormData({ isClusterUpgradeAcceptedLicense: event.target.checked });
  };

  const upgradeBundle = upgradeDetails?.bundle;

  const dialogControls = (
    <CustomDialogControls actionButtonLabel="Upgrade" onCancel={onClose} onAction={onNext} isActionDisabled={!isValid}>
      {upgradeBundle && upgradeBundle.licenseStatus !== AdcmLicenseStatus.Absent && (
        <Checkbox
          label={
            <>
              I accept <LinkToLicenseText bundleId={upgradeBundle.id} />
            </>
          }
          checked={
            // show checked when user set manual check in this iteration or earlier
            formData.isClusterUpgradeAcceptedLicense || upgradeBundle.licenseStatus === AdcmLicenseStatus.Accepted
          }
          disabled={upgradeBundle.licenseStatus === AdcmLicenseStatus.Accepted}
          onChange={handleChangeAcceptedUpgradeLicense}
        />
      )}
    </CustomDialogControls>
  );

  return (
    <Dialog
      width="auto"
      minWidth="584px"
      title="Upgrade HostProvider"
      isOpen={true}
      onOpenChange={onClose}
      dialogControls={dialogControls}
    >
      <SelectUpgradeStep formData={formData} onChange={handleChangeFormData} />
    </Dialog>
  );
};

export default HostProviderUpgradeDialog;
