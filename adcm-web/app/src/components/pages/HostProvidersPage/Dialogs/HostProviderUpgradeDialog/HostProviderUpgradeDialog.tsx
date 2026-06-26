import type React from 'react';
import { useHostProviderUpgradeDialog } from '@pages/HostProvidersPage/Dialogs/HostProviderUpgradeDialog/useHostProviderUpgradeDialog';
import { UpgradeStepKey } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import { AdcmLicenseStatus } from '@models/adcm';
import { Checkbox, DialogV2, WarningMessage } from '@uikit';
import LinkToLicenseText from '@commonComponents/LinkToLicenseText/LinkToLicenseText';
import SelectUpgradeStep from './SelectUpgradeStep/SelectUpgradeStep';
import s from './UpgradeProviderDialog.module.scss';

const HostProviderUpgradeDialog: React.FC = () => {
  const {
    hostProvider,
    isValid,
    upgradeDetails,
    formData,
    startImpossibleReason,
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
        isConcernStepShown={false}
      />
    );
  }

  const handleChangeAcceptedUpgradeLicense = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleChangeFormData({ isClusterUpgradeAcceptedLicense: event.target.checked });
  };

  const upgradeBundle = upgradeDetails?.bundle;

  const dialogControls = (
    <CustomDialogControls>
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
    <DialogV2
      minWidth="584px"
      title="Upgrade Hostprovider"
      actionButtonLabel="Upgrade"
      onCancel={onClose}
      onAction={onNext}
      isActionDisabled={!isValid}
      dialogControls={dialogControls}
    >
      <SelectUpgradeStep formData={formData} onChange={handleChangeFormData} />
      {startImpossibleReason && (
        <WarningMessage className={s.upgradeProviderDialog__errorMessage}>{startImpossibleReason}</WarningMessage>
      )}
      {!startImpossibleReason && upgradeDetails?.description && (
        <WarningMessage className={s.upgradeProviderDialog__infoMessage} innerMaxHeight={200}>
          <div className={s.upgradeProviderDialog__infoMessageContent}>{upgradeDetails.description}</div>
        </WarningMessage>
      )}
    </DialogV2>
  );
};

export default HostProviderUpgradeDialog;
