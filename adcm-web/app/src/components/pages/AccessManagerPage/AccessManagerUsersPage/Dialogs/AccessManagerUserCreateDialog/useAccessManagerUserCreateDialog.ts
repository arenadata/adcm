import { useState, useMemo, useEffect } from 'react';
import { useStore, useDispatch } from '@hooks';
import { AdcmCreateUserPayload } from '@models/adcm';
import { createUser, close } from '@store/adcm/users/dialogs/createUserDialogSlice';
import { emailRegexp } from '@constants';

export interface CreateUserForm extends AdcmCreateUserPayload {
  confirmPassword: string;
}

export type UserFormErrors = Pick<CreateUserForm, 'confirmPassword' | 'email'>;

const initialFormData: CreateUserForm = {
  username: '',
  firstName: '',
  lastName: '',
  email: '',
  groups: [],
  password: '',
  confirmPassword: '',
  isSuperUser: false,
};

export const useAccessManagerUserCreateDialog = () => {
  const dispatch = useDispatch();

  const [formData, setFormData] = useState<CreateUserForm>(initialFormData);
  const [errorMessages, setErrorMessages] = useState<UserFormErrors>(initialFormData);

  const {
    isOpen,
    relatedData,
    relatedData: { isLoaded: isRelatedDataLoaded },
  } = useStore((s) => s.adcm.createUserDialog);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  useEffect(() => {
    setErrorMessages((prevState) => ({
      ...prevState,
      confirmPassword: formData.confirmPassword === formData.password ? '' : 'Confirm password must match password',
    }));
  }, [formData.confirmPassword, formData.password]);

  useEffect(() => {
    setErrorMessages((prevState) => ({
      ...prevState,
      email: emailRegexp.test(formData.email) ? '' : 'Email is not correct',
    }));
  }, [formData.email]);

  const isValid = useMemo(() => {
    return (
      formData.username &&
      formData.password &&
      formData.confirmPassword &&
      !errorMessages.confirmPassword &&
      formData.firstName &&
      formData.lastName &&
      !errorMessages.email
    );
  }, [formData, errorMessages]);

  const handleClose = () => {
    dispatch(close());
  };

  const handleCreate = () => {
    dispatch(
      createUser({
        username: formData.username,
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        groups: formData.groups,
        password: formData.password,
        isSuperUser: formData.isSuperUser,
      }),
    );
  };

  const handleChangeFormData = (changes: Partial<CreateUserForm>) => {
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
    errorMessages,
    onClose: handleClose,
    onCreate: handleCreate,
    onChangeFormData: handleChangeFormData,
  };
};
