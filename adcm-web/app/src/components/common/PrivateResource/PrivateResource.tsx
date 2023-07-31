import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useStore } from '@hooks';
import { AUTH_STATE } from '@store/userSlice';

const PrivateResource: React.FC<React.PropsWithChildren> = ({ children }) => {
  const needCheckSession = useStore((s) => s.user.needCheckSession);
  const authState = useStore((s) => s.user.authState);
  const location = useLocation();

  if (needCheckSession) {
    return null;
  }

  if (authState === AUTH_STATE.NOT_AUTH) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export default PrivateResource;
