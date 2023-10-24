import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useStore } from '@hooks';
import { AUTH_STATE } from '@store/authSlice';

const PrivateResource: React.FC<React.PropsWithChildren> = ({ children }) => {
  const needCheckSession = useStore((s) => s.auth.needCheckSession);
  const authState = useStore((s) => s.auth.authState);
  const location = useLocation();

  if (needCheckSession) {
    return null;
  }

  if (authState === AUTH_STATE.NotAuth) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateResource;
