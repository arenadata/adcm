import React from 'react';
import { Checkbox, Dialog } from '@uikit';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import { AdcmLicenseStatus } from '@models/adcm';
import { useUpgradeClusterDialog } from './useUpgradeClusterDialog';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';
import SelectUpgradeStep from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/SelectUpgradeStep/SelectUpgradeStep';
import { UpgradeStepKey } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';
import ServicesLicensesStep from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/ServicesLicensesStep/ServicesLicensesStep';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';

const UpgradeClusterDialog = () => {
  const { cluster, isValid, upgradeDetails, formData, handleChangeFormData, onSubmit, onNext, onClose, currentStep } =
    useUpgradeClusterDialog();

  if (!cluster) return null;

  // for last step with set upgrade run config use DynamicActionDialog
  if (upgradeDetails && currentStep === UpgradeStepKey.UpgradeRunConfig) {
    return (
      <DynamicActionDialog
        clusterId={cluster.id}
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
      title="Upgrade Cluster"
      isOpen={true}
      onOpenChange={onClose}
      dialogControls={dialogControls}
    >
      {currentStep === UpgradeStepKey.SelectUpgrade && (
        <SelectUpgradeStep formData={formData} onChange={handleChangeFormData} />
      )}
      {currentStep === UpgradeStepKey.ServicesLicenses && (
        <ServicesLicensesStep formData={formData} onChange={handleChangeFormData} />
      )}
    </Dialog>
  );
};

export default UpgradeClusterDialog;
