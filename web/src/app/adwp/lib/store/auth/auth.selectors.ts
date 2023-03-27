import { createFeatureSelector, createSelector } from '@ngrx/store';

import { AuthState } from './auth.reducers';

export const getAuthState = createFeatureSelector<AuthState>('auth');

export const isAuthenticated = createSelector(
  getAuthState,
  state => state.isValid
);

export const isAuthChecking = createSelector(
  getAuthState,
  state => state.checking
);
