import { useStore, useDispatch, useForm } from '@hooks';
import {
  acceptPrototypeLicense,
  closeHostProviderUpgradeDialog,
  loadHostProviderUpgradeDetails,
  loadHostProviderUpgrades,
  runHostProviderUpgrade,
} from '@store/adcm/hostProviders/hostProviderUpgradesSlice';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { UpgradeHostProviderFormData } from './HostProviderUpgradeDialog.types';
import { AdcmUpgradeRunConfig, AdcmLicenseStatus } from '@models/adcm';
import { UpgradeStepKey } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';

const getInitialFormData = (): UpgradeHostProviderFormData => ({
  upgradeId: null,
  isClusterUpgradeAcceptedLicense: false,
});

export const useHostProviderUpgradeDialog = () => {
  const dispatch = useDispatch();

  const hostProvider = useStore(({ adcm }) => adcm.hostProviderUpgrades.dialog.hostProvider);
  const upgradesDetails = useStore(({ adcm }) => adcm.hostProviderUpgrades.relatedData.upgradesDetails);

  const [currentStep, setCurrentStep] = useState(UpgradeStepKey.SelectUpgrade);

  const { formData, handleChangeFormData, setFormData } = useForm<UpgradeHostProviderFormData>(getInitialFormData());

  const handleClose = useCallback(() => {
    setCurrentStep(UpgradeStepKey.SelectUpgrade);
    setFormData(getInitialFormData());
    dispatch(closeHostProviderUpgradeDialog());
  }, [dispatch, setCurrentStep, setFormData]);

  // load hostProvider short upgrades list, when hostProvider was changed (use for select on first step)
  useEffect(() => {
    if (hostProvider) {
      dispatch(loadHostProviderUpgrades(hostProvider.id));
    }
  }, [dispatch, hostProvider]);

  // upgradesDetails load from backend to cache-object (upgradeId => upgradesDetail)
  // upgradesDetail load only one time (while upgrade dialog is open)
  const upgradeDetails = (formData.upgradeId && upgradesDetails[formData.upgradeId]) || null;

  // load upgradesDetail after select upgrade
  useEffect(() => {
    if (hostProvider && formData.upgradeId && !upgradeDetails) {
      dispatch(loadHostProviderUpgradeDetails({ hostProviderId: hostProvider.id, upgradeId: formData.upgradeId }));
    }
  }, [dispatch, hostProvider, upgradeDetails, formData.upgradeId]);

  // after user select upgrade (first step), after accept licenses of all relative service prototypes (second step)
  // we send request for accept license for upgrade prototype
  const acceptUpgradeLicense = useCallback(() => {
    const upgradeBundle = upgradeDetails?.bundle;
    if (upgradeBundle?.licenseStatus === AdcmLicenseStatus.Unaccepted && formData.isClusterUpgradeAcceptedLicense) {
      dispatch(acceptPrototypeLicense(upgradeBundle.prototypeId))
        .unwrap()
        .catch(() => {
          // if this request will reject then we close and clear dialog. No reasons for set config without accept license
          handleClose();
        });
    }
  }, [dispatch, formData, upgradeDetails, handleClose]);

  useEffect(() => {
    // when switch to last step with upgrade settings, try to accept upgrade license
    if (currentStep === UpgradeStepKey.UpgradeRunConfig) {
      acceptUpgradeLicense();
    }
  }, [currentStep, acceptUpgradeLicense]);

  const handleNext = () => {
    if (currentStep === UpgradeStepKey.SelectUpgrade) {
      if (upgradeDetails) {
        // switch to last step with set configs
        setCurrentStep(UpgradeStepKey.UpgradeRunConfig);
      }
    }
  };

  const handleSubmit = (upgradeRunConfig: AdcmUpgradeRunConfig) => {
    if (hostProvider && upgradeDetails) {
      dispatch(
        runHostProviderUpgrade({
          hostProvider,
          upgradeId: upgradeDetails.id,
          upgradeRunConfig,
        }),
      );
      handleClose();
    }
  };

  const isValid = useMemo(() => {
    // if not load current upgradeDetails (long loading or not select upgrade) set isValid = false, for disabled Next button
    if (!upgradeDetails) return false;

    // if upgrade have no acceptance license then disable Next button. This condition will work on very step
    if (
      upgradeDetails.bundle.licenseStatus === AdcmLicenseStatus.Unaccepted &&
      !formData.isClusterUpgradeAcceptedLicense
    ) {
      return false;
    }

    return true;
  }, [formData, upgradeDetails]);

  return {
    currentStep,
    isValid,
    hostProvider,
    formData,
    handleChangeFormData,
    upgradeDetails,
    onClose: handleClose,
    onSubmit: handleSubmit,
    onNext: handleNext,
  };
};
