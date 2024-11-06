import { useMemo, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion, AdcmLicenseStatus } from '@models/adcm';
import {
  cleanupClustersActions,
  createCluster,
  loadPrototypesRelatedData,
} from '@store/adcm/clusters/clustersActionsSlice';
import { isClusterNameValid, isNameUniq, required } from '@utils/validationsUtils';

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

  const clusters = useStore((s) => s.adcm.clusters.clusters);
  const {
    createDialog: { isOpen },
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.clustersActions);

  useEffect(() => {
    if (isOpen) {
      dispatch(loadPrototypesRelatedData());
    } else {
      setFormData(initialFormData);
    }
  }, [isOpen, dispatch, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Cluster name field is required') ||
        (isClusterNameValid(formData.name) ? undefined : 'Cluster name field is incorrect') ||
        (isNameUniq(formData.name, clusters) ? undefined : 'Cluster with the same name already exists'),
    });
  }, [formData, clusters, setErrors]);

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
