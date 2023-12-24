import { useStore, useDispatch, useForm } from '@hooks';
import {
  acceptPrototypeLicense,
  closeClusterUpgradeDialog,
  loadClusterUpgradeDetails,
  loadClusterUpgrades,
  runClusterUpgrade,
} from '@store/adcm/clusters/clusterUpgradesSlice';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { UpgradeClusterFormData, UpgradeStepKey } from './UpgradeClusterDialog.types';
import { AdcmUpgradeRunConfig, AdcmLicenseStatus } from '@models/adcm';

const getInitialFormData = (): UpgradeClusterFormData => ({
  upgradeId: null,
  isClusterUpgradeAcceptedLicense: false,
  servicesPrototypesAcceptedLicense: new Set(),
});

export const useUpgradeClusterDialog = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.clusterUpgrades.dialog.cluster);
  const upgradesDetails = useStore(({ adcm }) => adcm.clusterUpgrades.relatedData.upgradesDetails);

  const [currentStep, setCurrentStep] = useState(UpgradeStepKey.SelectUpgrade);

  const { formData, handleChangeFormData, setFormData } = useForm<UpgradeClusterFormData>(getInitialFormData());

  const handleClose = useCallback(() => {
    setCurrentStep(UpgradeStepKey.SelectUpgrade);
    setFormData(getInitialFormData());
    dispatch(closeClusterUpgradeDialog());
  }, [dispatch, setCurrentStep, setFormData]);

  // load cluster short upgrades list, when cluster was changed (use for select on first step)
  useEffect(() => {
    if (cluster) {
      dispatch(loadClusterUpgrades(cluster.id));
    }
  }, [dispatch, cluster]);

  // upgradesDetails load from backend to cache-object (upgradeId => upgradesDetail)
  // upgradesDetail load only one time (while upgrade dialog is open)
  const upgradeDetails = (formData.upgradeId && upgradesDetails[formData.upgradeId]) || null;

  // load upgradesDetail after select upgrade
  useEffect(() => {
    if (cluster && formData.upgradeId && !upgradeDetails) {
      dispatch(loadClusterUpgradeDetails({ clusterId: cluster.id, upgradeId: formData.upgradeId }));
    }
  }, [dispatch, cluster, upgradeDetails, formData.upgradeId]);

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
        // if upgrade have some unaccepted relative service prototype then switch to step with form for accept service license
        if (upgradeDetails.bundle.unacceptedServicesPrototypes.length > 0) {
          setCurrentStep(UpgradeStepKey.ServicesLicenses);
        } else {
          // switch to last step with set configs
          setCurrentStep(UpgradeStepKey.UpgradeRunConfig);
        }
      }
    }

    if (currentStep === UpgradeStepKey.ServicesLicenses) {
      // switch to last step with set configs
      setCurrentStep(UpgradeStepKey.UpgradeRunConfig);
    }
  };

  const handleSubmit = (upgradeRunConfig: AdcmUpgradeRunConfig) => {
    if (cluster && upgradeDetails) {
      dispatch(
        runClusterUpgrade({
          cluster,
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

    if (currentStep === UpgradeStepKey.ServicesLicenses) {
      // when user accept relative service license - we send request on server on success we append servicePrototypeId to formData.servicesPrototypesAcceptedLicense
      // if count of element in formData.servicesPrototypesAcceptedLicense != unacceptedServicesPrototypes.length then user accept not all relative services
      // and user should accept all services (disable Next button)
      if (
        upgradeDetails.bundle.unacceptedServicesPrototypes.length !== formData.servicesPrototypesAcceptedLicense.size
      ) {
        return false;
      }
    }

    return true;
  }, [currentStep, formData, upgradeDetails]);

  return {
    currentStep,
    isValid,
    cluster,
    formData,
    handleChangeFormData,
    upgradeDetails,
    onClose: handleClose,
    onSubmit: handleSubmit,
    onNext: handleNext,
  };
};
