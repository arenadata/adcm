import React from 'react';
import { useCheckSession } from '@hooks';

const UserSession = ({ children }: React.PropsWithChildren<unknown>) => {
  useCheckSession();
  return <>{children}</>;
};

export default UserSession;
