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
import { IRoot } from '@app/core/types/api';
import { environment } from '@env/environment';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { of } from 'rxjs';
import { catchError, delay, exhaustMap, filter, map, switchMap, withLatestFrom } from 'rxjs/operators';

import { State } from '../store';
import { loadRoot, loadStack, rootError, rootSuccess, stackSuccess } from './api.reducer';
import { ApiService } from './api.service';

@Injectable()
export class ApiEffects {
  root$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadRoot),
      exhaustMap(() =>
        this.api.get<IRoot>(environment.apiRoot).pipe(
          map(root => rootSuccess({ root })),
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
        this.api.get<IRoot>(environment.apiRoot).pipe(
          map(root => rootSuccess({ root })),
          catchError(() => of(rootError()))
        )
      )
    )
  );

  stack$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadStack),
      withLatestFrom(this.store, (actions, store) => store.api),
      filter(api => api.root && !api.stack),
      exhaustMap(api => this.api.get<IRoot>(api.root.stack).pipe(map(stack => stackSuccess({ stack }))))
    )
  );

  constructor(private actions$: Actions, private api: ApiService, private store: Store<State>) {}
}
