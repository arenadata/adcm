import React from 'react';
import { useCheckSession } from '@hooks';
import { useCleanupUserTableSettings } from './useCleanupUserTableSettings';

const UserSession = ({ children }: React.PropsWithChildren<unknown>) => {
  useCheckSession();
  useCleanupUserTableSettings();
  return <>{children}</>;
};

export default UserSession;
