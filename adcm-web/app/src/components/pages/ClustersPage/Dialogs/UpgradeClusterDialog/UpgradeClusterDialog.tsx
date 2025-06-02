import type React from 'react';
import { Checkbox, DialogV2 } from '@uikit';
import { AdcmLicenseStatus } from '@models/adcm';
import { useUpgradeClusterDialog } from './useUpgradeClusterDialog';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';
import SelectUpgradeStep from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/SelectUpgradeStep/SelectUpgradeStep';
import { UpgradeStepKey } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';
import ServicesLicensesStep from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/ServicesLicensesStep/ServicesLicensesStep';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import CustomDialogControlsV2 from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControlsV2';

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
    <CustomDialogControlsV2>
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
    </CustomDialogControlsV2>
  );

  return (
    <DialogV2
      minWidth="584px"
      title="Upgrade Cluster"
      onAction={onNext}
      onCancel={onClose}
      dialogControls={dialogControls}
      actionButtonLabel="Upgrade"
      isActionDisabled={!isValid}
    >
      {currentStep === UpgradeStepKey.SelectUpgrade && (
        <SelectUpgradeStep formData={formData} onChange={handleChangeFormData} />
      )}
      {currentStep === UpgradeStepKey.ServicesLicenses && (
        <ServicesLicensesStep formData={formData} onChange={handleChangeFormData} />
      )}
    </DialogV2>
  );
};

export default UpgradeClusterDialog;
