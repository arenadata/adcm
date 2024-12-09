import type { AnyAction, Middleware } from 'redux';
import { isRejectedWithValue } from '@reduxjs/toolkit';
import { logout } from '../authSlice';
import type { RootState } from '../store';
import type { RequestError } from '@api/httpClient';

export const apiMiddleware: Middleware<
  // biome-ignore lint/complexity/noBannedTypes:
  {},
  RootState
> = (storeApi) => (next) => (action) => {
  if (isRejectedWithValue(action)) {
    const response = (action.payload as RequestError)?.response;
    if (response?.status === 401) {
      // not reasons call logout after mistake login
      if (action.type !== 'auth/login/rejected') {
        storeApi.dispatch(logout() as unknown as AnyAction);
      }
    }
  }
  next(action);
};
