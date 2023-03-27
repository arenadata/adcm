import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { map, switchMap, catchError, tap } from 'rxjs/operators';
import { of } from 'rxjs';

import { authSuccess, authFailed, authLogin, authLogout, authCheck } from './auth.actions';
import { AuthService } from '../../services/auth.service';
import { DjangoHttpErrorResponse } from '../../models/django-http-error-response';

@Injectable()
export class AuthEffects {

  check$ = createEffect(() =>
    this.actions$.pipe(
      ofType(authCheck),
      switchMap(() => this.authService.checkAuth().pipe(
        tap((status) => this.authService.setTokenCookieName(status.csrftoken)),
        map((auth) => authSuccess({ username: auth.username })),
        catchError(() => of(authFailed({ message: '' }))),
      )),
    ),
    { useEffectsErrorHandler: true }
  );

  auth$ = createEffect(() =>
    this.actions$.pipe(
      ofType(authLogin),
      switchMap(a =>
        this.authService.login(a.username, a.password).pipe(
          map(() => authCheck()),
          catchError((err: DjangoHttpErrorResponse) => of(authFailed({ message: err.error.desc }))),
        )),
      ),
    { useEffectsErrorHandler: true }
  );

  logout$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(authLogout),
        switchMap(() => this.authService.logout()),
      ),
    { dispatch: false }
  );

  constructor(
    private actions$: Actions,
    private authService: AuthService
  ) {}

}
