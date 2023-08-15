import React from 'react';
import NonAuthLayout from '@layouts/NonAuthLayout/NonAuthLayout';
import { useStore } from '@hooks';
import LoginForm from '@pages/LoginPage/LoginForm/LoginForm';
import { Navigate, useLocation } from 'react-router-dom';
import { AUTH_STATE } from '@store/userSlice';

import s from './LoginPage.module.scss';
import Text from '@uikit/Text/Text';
import cn from 'classnames';

type RedirectLocationState = {
  from: string;
};

const LoginPage: React.FC = () => {
  const { authState } = useStore((s) => s.user);

  const location = useLocation();
  const from = (location.state as RedirectLocationState)?.from || '/';

  if (authState === AUTH_STATE.Authed) {
    return <Navigate to={from} replace />;
  }

  return (
    <NonAuthLayout>
      <div className={s.loginPage}>
        <Text variant="h1" className={cn('green-text', s.loginPage__title)}>
          Arenadata Cluster Manager
        </Text>
        <LoginForm />
      </div>
    </NonAuthLayout>
  );
};

export default LoginPage;
