// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Action, createAction, createFeatureSelector, createReducer, createSelector, on, props } from '@ngrx/store';
import { of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { AuthService } from './auth.service';

export const authCheck = createAction('[Auth] Check');
export const authLogin = createAction('[Auth] Login', props<{ login: string; password: string }>());
export const authSuccess = createAction('[Auth] LoginSuccess', props<{ login: string }>());
export const authFaled = createAction('[Auth] LoginFaled', props<{ message: string }>());
export const authLogout = createAction('[Auth] Logout');

export interface AuthState {
  isValid: boolean;
  message: string;
}

const initialState: AuthState = {
  isValid: false,
  message: '',
};

const reducer = createReducer(
  initialState,
  on(authSuccess, state => ({ isValid: true, message: 'Auth is success.' })),
  on(authFaled, (state, { message }) => ({ isValid: false, message })),
  on(authLogout, state => ({ isValid: false, message: '' }))
);

export function authReducer(state: AuthState, action: Action) {
  return reducer(state, action);
}

export const getAuthState = createFeatureSelector<AuthState>('auth');
export const isAuthenticated = createSelector(
  getAuthState,
  state => state.isValid
);

@Injectable()
export class AuthEffects {
  check$ = createEffect(() =>
    this.actions$.pipe(
      ofType(authCheck),
      map(() =>
        this.authService.auth.token
          ? authSuccess({ login: this.authService.auth.login })
          : authFaled({ message: 'User is not authorized!' })
      )
    )
  );

  auth$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(authLogin),
        switchMap(a =>
          this.authService.login(a.login, a.password).pipe(
            map(() => authSuccess({ login: a.login })),
            catchError(() => of(authFaled({ message: 'Incorrect password or user.' })))
          )
        )
      ),
    { resubscribeOnError: true }
  );

  logout$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(authLogout),
        tap(() => this.authService.logout())
      ),
    { dispatch: false }
  );

  constructor(private actions$: Actions, private authService: AuthService) {}
}
