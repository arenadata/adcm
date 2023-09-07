import { useState, useMemo, useCallback } from 'react';
import { useDispatch } from '@hooks';
import { changePassword } from '@store/adcm/profile/profileSlice';

interface ChangePasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

const initialFormData: ChangePasswordFormData = {
  currentPassword: '',
  newPassword: '',
  confirmNewPassword: '',
};

export const useChangePasswordForm = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<ChangePasswordFormData>(initialFormData);

  const isValid = useMemo(() => {
    const { currentPassword, newPassword, confirmNewPassword } = formData;

    if (currentPassword !== '') {
      if (newPassword !== '' && confirmNewPassword !== '') {
        return newPassword === confirmNewPassword;
      }
    }
    return false;
  }, [formData]);

  const submitForm = useCallback(() => {
    const { currentPassword, newPassword } = formData;
    dispatch(
      changePassword({
        currentPassword,
        newPassword,
      }),
    );
  }, [formData, dispatch]);

  const handleChangeFormData = (changes: Partial<ChangePasswordFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isValid,
    formData,
    submitForm,
    onChangeFormData: handleChangeFormData,
  };
};
