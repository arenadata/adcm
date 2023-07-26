import { useState, useMemo, useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmPrototypeVersions, AdcmPrototypeVersion } from '@models/adcm';
import { close, createHostProvider } from '@store/adcm/hostProviders/dialogs/createHostProviderDialogSlice';

interface CreateHostProviderFormData {
  prototype: AdcmPrototypeVersions | null;
  prototypeVersion: AdcmPrototypeVersion | null;
  name: string;
  description: string;
}

const initialFormData: CreateHostProviderFormData = {
  prototype: null,
  prototypeVersion: null,
  name: '',
  description: '',
};

export const useCreateHostProviderDialog = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<CreateHostProviderFormData>(initialFormData);

  const {
    isOpen,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.createHostProviderDialog);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const isValid = useMemo(() => {
    return formData.prototypeVersion !== null && formData.name;
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
        }),
      );
    }
  };

  const handleChangeFormData = (changes: Partial<CreateHostProviderFormData>) => {
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
