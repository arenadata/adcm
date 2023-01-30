import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { of } from 'rxjs';
import { catchError, delay, exhaustMap, filter, map, switchMap, withLatestFrom } from 'rxjs/operators';

import { AdwpState } from '../state';
import { IRoot } from '../../models/root';
import { ApiService } from '../../services/api.service';
import { loadRoot, loadStack, rootError, rootSuccess, stackSuccess } from './api.reducer';

export const API_ROOT = '/api/v1/';

@Injectable()
export class ApiEffects {
  root$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadRoot),
      exhaustMap(() =>
        this.api.get<IRoot>(API_ROOT).pipe(
          map((root) => rootSuccess({ root })),
          catchError(() => of(rootError()))
        )
      )
    )
  );

  retry$ = createEffect(() =>
    this.actions$.pipe(
      ofType(rootError),
      delay(3000),
      switchMap(() =>
        this.api.get<IRoot>(API_ROOT).pipe(
          map((root) => rootSuccess({ root })),
          catchError(() => of(rootError()))
        )
      )
    )
  );

  stack$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadStack),
      withLatestFrom(this.store, (actions, store) => store.api),
      filter((api) => api.root && !api.stack),
      exhaustMap((api) =>
        this.api
          .get<IRoot>(api.root.stack)
          .pipe(map((stack) => stackSuccess({ stack })))
      )
    )
  );

  constructor(
    private actions$: Actions,
    private api: ApiService,
    private store: Store<AdwpState>
  ) {}
}
