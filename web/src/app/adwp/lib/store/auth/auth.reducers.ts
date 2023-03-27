import { Action, createReducer, on } from '@ngrx/store';
import { authSuccess, authFailed, authLogout, authCheck } from './auth.actions';

export interface AuthState {
  isValid: boolean;
  message: string;
  checking: boolean;
}

const initialState: AuthState = {
  isValid: false,
  message: '',
  checking: false,
};

const reducer = createReducer(
  initialState,
  on(authCheck, state => ({ isValid: false, message: '', checking: true })),
  on(authSuccess, state => ({ isValid: true, message: 'Auth is success.', checking: false })),
  on(authFailed, (state, { message }) => ({ isValid: false, message, checking: false })),
  on(authLogout, state => ({ isValid: false, message: '', checking: false })),
);

export function authReducer(state: AuthState, action: Action): AuthState {
  return reducer(state, action);
}
