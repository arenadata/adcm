import React, { useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { clearError, login } from '@store/authSlice';
import Input from '@uikit/Input/Input';
import InputPassword from '@uikit/InputPassword/InputPassword';
import Button from '@uikit/Button/Button';
import FormField from '@uikit/FormField/FormField';

import s from './LoginForm.module.scss';
import FormFieldsContainer from '@uikit/FormField/FormFieldsContainer';

const LoginForm: React.FC = () => {
  const dispatch = useDispatch();
  const { hasError, message } = useStore((s) => s.auth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const errorMessage = hasError ? message : undefined;

  const handleUsernameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(clearError());
    setUsername(event.target.value);
  };

  const handlePasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(clearError());
    setPassword(event.target.value);
  };

  const handleSubmit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    dispatch(
      login({
        username,
        password,
      }),
    );
  };
  return (
    <form onSubmit={handleSubmit} autoComplete="off">
      <FormFieldsContainer>
        <FormField label="User" error={errorMessage}>
          <Input
            value={username}
            type="text"
            name="username"
            onChange={handleUsernameChange}
            placeholder="Enter username"
            autoComplete="username"
          />
        </FormField>
        <FormField label="Password" hasError={hasError}>
          <InputPassword
            value={password}
            placeholder="Enter password"
            onChange={handlePasswordChange}
            autoComplete="current-password"
          />
        </FormField>

        <Button type="submit" className={s.loginForm__submit} hasError={hasError} disabled={hasError}>
          Sign in
        </Button>
      </FormFieldsContainer>
    </form>
  );
};
export default LoginForm;
