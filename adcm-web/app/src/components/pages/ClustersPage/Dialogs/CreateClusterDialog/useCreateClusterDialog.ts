import { useMemo, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion, AdcmLicenseStatus } from '@models/adcm';
import { cleanupClustersActions, createCluster } from '@store/adcm/clusters/clustersActionsSlice';
import { isClusterNameValid, required } from '@utils/validationsUtils';

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

  const { formData, setFormData, handleChangeFormData, errors, setErrors } =
    useForm<CreateClusterFormData>(initialFormData);

  const {
    isCreateClusterDialogOpen: isOpen,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.clustersActions);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Cluster name field is required') ||
        (isClusterNameValid(formData.name) ? undefined : 'Cluster name field is incorrect'),
    });
  }, [formData, setErrors]);

  const isValid = useMemo(() => {
    return (
      formData.productVersion !== null &&
      isClusterNameValid(formData.name) &&
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

  return {
    isOpen,
    isValid,
    formData,
    errors,
    relatedData,
    isRelatedDataLoaded,
    onClose: handleClose,
    onCreate: handleCreate,
    onChangeFormData: handleChangeFormData,
  };
};
