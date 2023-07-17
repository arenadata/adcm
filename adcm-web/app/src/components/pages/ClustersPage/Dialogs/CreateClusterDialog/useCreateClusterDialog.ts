import { useState, useMemo, useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion } from '@models/adcm';
import { close, createCluster } from '@store/adcm/clusters/dialogs/createClusterDialogSlice';

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
    adcm: {
      createClusterDialog: {
        isOpen,
        relatedData,
        relatedData: { isLoaded: isRelatedDataLoaded },
      },
    },
  } = useStore();

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const isValid = useMemo(() => {
    return formData.productVersion !== null && formData.name && formData.isUserAcceptedLicense;
  }, [formData]);

  const handleClose = () => {
    dispatch(close());
  };

  const handleCreate = () => {
    if (formData.productVersion) {
      dispatch(
        createCluster({
          name: formData.name,
          description: formData.description,
          prototypeId: formData.productVersion.id,
          isLicenseAccepted: formData.productVersion?.isLicenseAccepted ?? false,
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
