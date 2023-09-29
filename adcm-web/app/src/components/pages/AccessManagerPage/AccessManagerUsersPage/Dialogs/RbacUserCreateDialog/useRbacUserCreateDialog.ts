import { useDispatch, useStore } from '@hooks';
import { closeUserCreateDialog, createUser } from '@store/adcm/users/usersActionsSlice';
import { RbacUserFormData } from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm.types';
import { useEffect } from 'react';
import { useForm } from '@hooks/useForm';
import { isEmailValid, required } from '@utils/validationsUtils';

const initialFormData: RbacUserFormData = {
  username: '',
  firstName: '',
  lastName: '',
  email: '',
  groups: [],
  password: '',
  confirmPassword: '',
  isSuperUser: false,
};

export const useRbacUserCreateDialog = () => {
  const dispatch = useDispatch();
  const isOpen = useStore((s) => s.adcm.usersActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.usersActions.createDialog.isCreating);
  const groups = useStore((s) => s.adcm.usersActions.relatedData.groups);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<RbacUserFormData>(initialFormData);

  useEffect(() => {
    setErrors({
      username: required(formData.username) ? undefined : 'Username field is required',
      password: required(formData.password) ? undefined : 'Password field is required',
      firstName: required(formData.firstName) ? undefined : 'First Name field is required',
      lastName: required(formData.lastName) ? undefined : 'Last Name field is required',
      confirmPassword:
        formData.confirmPassword === formData.password ? undefined : 'Confirm password must match password',
      email: isEmailValid(formData.email) ? undefined : 'Email is not correct',
    });
  }, [formData, setErrors]);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen, setFormData]);

  const handleClose = () => {
    dispatch(closeUserCreateDialog());
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

  return {
    isOpen,
    groups,
    onChangeFormData: handleChangeFormData,
    isValid: isValid && !isCreating,
    formData,
    onClose: handleClose,
    onSubmit: handleCreate,
    errors,
  };
};
