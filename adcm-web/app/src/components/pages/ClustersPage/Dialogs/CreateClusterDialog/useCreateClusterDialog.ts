import { useState, useMemo, useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion, AdcmLicenseStatus } from '@models/adcm';
import { cleanupClustersActions, createCluster } from '@store/adcm/clusters/clustersActionsSlice';

interface CreateClusterFormData {
  product: AdcmPrototypeVersions | null;
  productVersion: AdcmPrototypeVersion | null;
  name: string;
  description: string;
  isUserAcceptedLicense: boolean;
}

const initialFormData: CreateClusterFormData = {
  product: null,
  productVersion: null,
  name: '',
  description: '',
  isUserAcceptedLicense: false,
};

export const useCreateClusterDialog = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<CreateClusterFormData>(initialFormData);

  const {
    isCreateClusterDialogOpen: isOpen,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.clustersActions);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const isValid = useMemo(() => {
    return (
      formData.productVersion !== null &&
      formData.name &&
      (formData.productVersion.licenseStatus === AdcmLicenseStatus.Absent || formData.isUserAcceptedLicense)
    );
  }, [formData]);

  const handleClose = () => {
    dispatch(cleanupClustersActions());
  };

  const handleCreate = () => {
    if (formData.productVersion) {
      dispatch(
        createCluster({
          name: formData.name,
          description: formData.description,
          prototypeId: formData.productVersion.id,
          isNeedAcceptLicense: formData.productVersion.licenseStatus === AdcmLicenseStatus.Unaccepted,
        }),
      );
    }
  };

  const handleChangeFormData = (changes: Partial<CreateClusterFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isOpen,
    isValid,
    formData,
    relatedData,
    isRelatedDataLoaded,
    onClose: handleClose,
    onCreate: handleCreate,
    onChangeFormData: handleChangeFormData,
  };
};
