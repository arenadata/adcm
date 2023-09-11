import { useState, useMemo, useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmClusterUpgrade, AdcmLicenseStatus } from '@models/adcm';
import { cleanupClustersActions, loadClusterUpgradeActionDetails } from '@store/adcm/clusters/clustersActionsSlice';

interface UpgradeClusterFormData {
  upgrade: AdcmClusterUpgrade | null;
  isUserAcceptedLicense: boolean;
}

const initialFormData: UpgradeClusterFormData = {
  upgrade: null,
  isUserAcceptedLicense: false,
};

export const useUpgradeClusterDialog = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<UpgradeClusterFormData>(initialFormData);

  const isOpen = useStore(({ adcm }) => adcm.clustersActions.isUpgradeClusterDialogOpen);
  const cluster = useStore(({ adcm }) => adcm.clustersActions.cluster);
  const relatedData = useStore(({ adcm }) => adcm.clustersActions.relatedData);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const isValid = useMemo(() => {
    return (
      formData.upgrade &&
      (formData.upgrade.licenseStatus === AdcmLicenseStatus.Absent || formData.isUserAcceptedLicense)
    );
  }, [formData]);

  const handleClose = () => {
    dispatch(cleanupClustersActions());
  };

  const handleUpgrade = () => {
    // TODO: blocked by schema and config implementations
  };

  const handleChangeFormData = (changes: Partial<UpgradeClusterFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  const handleLoadUpgradeActionDetails = (upgradeId: number) => {
    if (cluster) {
      dispatch(loadClusterUpgradeActionDetails({ clusterId: cluster?.id, upgradeId }));
    }
  };

  return {
    isOpen,
    isValid,
    cluster,
    formData,
    relatedData,
    onClose: handleClose,
    onUpgrade: handleUpgrade,
    onChangeFormData: handleChangeFormData,
    onLoadUpgradeActionDetails: handleLoadUpgradeActionDetails,
  };
};
