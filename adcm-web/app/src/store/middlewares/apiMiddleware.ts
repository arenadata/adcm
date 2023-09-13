import { Middleware } from 'redux';
import { isRejectedWithValue } from '@reduxjs/toolkit';
import { logout } from '../authSlice';
import { StoreState, AppDispatch } from '../store';
import { RequestError } from '@api/httpClient';

export const apiMiddleware: Middleware<
  // eslint-disable-next-line @typescript-eslint/ban-types
  {},
  StoreState
> = (storeApi) => (next) => (action) => {
  if (isRejectedWithValue(action)) {
    const response = (action.payload as RequestError)?.response;
    if (response?.status === 401) {
      // not reasons call logout after mistake login
      if (action.type !== 'auth/login/rejected') {
        (storeApi.dispatch as AppDispatch)(logout());
      }
    }
  }
  next(action);
};
