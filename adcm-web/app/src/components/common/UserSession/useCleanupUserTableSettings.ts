import { useEffect } from 'react';
import { useStore, usePrevious } from '@hooks';
import { removeUserTableSettings } from '@utils/localStorageUtils';
import { AUTH_STATE } from '@store/authSlice';

export const useCleanupUserTableSettings = () => {
  const authState = useStore((s) => s.auth.authState);
  const username = useStore((s) => s.auth.username);

  const prevAuthState = usePrevious(authState);

  useEffect(() => {
    if (prevAuthState === AUTH_STATE.Authorizing && authState === AUTH_STATE.Authed) {
      removeUserTableSettings(username);
    }
  }, [prevAuthState, authState, username]);
};
