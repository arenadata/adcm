import { useDispatch, useStore, useForm } from '@hooks';
import { closeUserCreateDialog, createUser, loadGroups } from '@store/adcm/users/usersActionsSlice';
import { RbacUserFormData } from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm.types';
import { useEffect } from 'react';
import { isEmailValid, isNameUniq, required } from '@utils/validationsUtils';

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
  const users = useStore((s) => s.adcm.users.users);
  const isOpen = useStore((s) => s.adcm.usersActions.createDialog.isOpen);
  const isCreating = useStore((s) => s.adcm.usersActions.isActionInProgress);
  const groups = useStore((s) => s.adcm.usersActions.relatedData.groups);
  const authSettings = useStore((s) => s.auth.profile.authSettings);
  const isCurrentUserSuperUser = useStore((s) => s.auth.profile.isSuperUser);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<RbacUserFormData>(initialFormData);

  useEffect(() => {
    setErrors({
      username:
        (required(formData.username) ? undefined : 'Username field is required') ||
        (isNameUniq(
          formData.username,
          users.map((user) => ({ ...user, name: user.username })),
        )
          ? undefined
          : 'User with the same username already exists'),
      password:
        (required(formData.password) ? undefined : 'Password field is required') ||
        (formData.password.length >= authSettings.minPasswordLength &&
        formData.password.length <= authSettings.maxPasswordLength
          ? undefined
          : `Password should be greater than ${authSettings.minPasswordLength - 1}
          and less than ${authSettings.maxPasswordLength + 1}`),
      firstName: required(formData.firstName) ? undefined : 'First Name field is required',
      lastName: required(formData.lastName) ? undefined : 'Last Name field is required',
      confirmPassword:
        formData.confirmPassword === formData.password ? undefined : 'Confirm password must match password',
      email: isEmailValid(formData.email) ? undefined : 'Email is not correct',
    });
  }, [formData, users, authSettings, setErrors]);

  useEffect(() => {
    if (isOpen) {
      dispatch(loadGroups());
    } else {
      setFormData(initialFormData);
    }
  }, [dispatch, isOpen, setFormData]);

  const handleClose = () => {
    dispatch(closeUserCreateDialog());
  };

  const handleCreate = () => {
    const userData = {
      username: formData.username,
      firstName: formData.firstName,
      lastName: formData.lastName,
      email: formData.email,
      groups: formData.groups,
      password: formData.password,
    };

    dispatch(
      createUser({
        ...userData,
        ...(isCurrentUserSuperUser && { isSuperUser: formData.isSuperUser }),
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
    isCurrentUserSuperUser,
  };
};
