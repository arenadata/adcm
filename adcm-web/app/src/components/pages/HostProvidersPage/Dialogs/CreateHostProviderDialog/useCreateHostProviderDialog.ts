import { useMemo, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion, AdcmLicenseStatus } from '@models/adcm';
import { close, createHostProvider } from '@store/adcm/hostProviders/dialogs/createHostProviderDialogSlice';
import { isHostProviderNameValid, isNameUniq, required } from '@utils/validationsUtils';

interface CreateHostProviderFormData {
  prototype: AdcmPrototypeVersions | null;
  prototypeVersion: AdcmPrototypeVersion | null;
  name: string;
  description: string;
  isUserAcceptedLicense: boolean;
}

const initialFormData: CreateHostProviderFormData = {
  prototype: null,
  prototypeVersion: null,
  name: '',
  description: '',
  isUserAcceptedLicense: false,
};

export const useCreateHostProviderDialog = () => {
  const dispatch = useDispatch();

  const { formData, setFormData, handleChangeFormData, errors, setErrors } =
    useForm<CreateHostProviderFormData>(initialFormData);

  const hostProviders = useStore((s) => s.adcm.hostProviders.hostProviders);
  const {
    isOpen,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.createHostProviderDialog);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Hostprovider name field is required') ||
        (isHostProviderNameValid(formData.name) ? undefined : 'Hostprovider name field is incorrect') ||
        (isNameUniq(formData.name, hostProviders) ? undefined : 'Hostprovider with the same name already exists'),
    });
  }, [formData, hostProviders, setErrors]);

  const isValid = useMemo(() => {
    return (
      formData.prototypeVersion !== null &&
      formData.name &&
      (formData.prototypeVersion.licenseStatus === AdcmLicenseStatus.Absent || formData.isUserAcceptedLicense)
    );
  }, [formData]);

  const handleClose = () => {
    dispatch(close());
  };

  const handleCreate = () => {
    if (formData.prototypeVersion) {
      dispatch(
        createHostProvider({
          name: formData.name,
          prototypeId: formData.prototypeVersion.id,
          description: formData.description,
          isNeededLicenseAcceptance: formData.prototypeVersion.licenseStatus === AdcmLicenseStatus.Unaccepted,
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
