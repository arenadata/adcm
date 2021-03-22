import {
  Action,
  createAction,
  createFeatureSelector,
  createReducer,
  createSelector,
  on,
  props,
} from '@ngrx/store';
import { ParamMap } from '@angular/router';

import { AdcmTypedEntity } from '../../models/entity';
import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { filter, map, switchMap, tap } from 'rxjs/operators';
import { Observable, zip } from 'rxjs';
import { ClusterService } from '@app/core';
import { TypeName } from '@app/core/types';


export const setPath = createAction('[Navigation] Set path', props<{ path: AdcmTypedEntity[] }>());
export const setPathOfRoute = createAction('[Navigation] Set path', props<{ params: ParamMap }>());

export interface NavigationState {
  path: AdcmTypedEntity[];
}

const initialState: NavigationState = {
  path: [],
};

const reducer = createReducer(
  initialState,
  on(setPath, (state, { path }) => ({ path })),
);

export function navigationReducer(state: NavigationState, action: Action) {
  return reducer(state, action);
}

export const getNavigationState = createFeatureSelector<NavigationState>('navigation');
export const getNavigationPath = createSelector(
  getNavigationState,
  state => state.path
);

@Injectable()
export class NavigationEffects {

  setPathOfRoute$ = createEffect(
    () =>
      this.actions$.pipe(
        ofType(setPathOfRoute),
        filter(action => !!action.params),
        switchMap(action => {
          const getters: Observable<AdcmTypedEntity>[] = action.params.keys.reduce((acc, param) => {
            const getter = this.detailService.entityGetter(param as TypeName, action.params);
            if (getter) {
              acc.push(getter);
            }

            return acc;
          }, []);

          return zip(...getters).pipe(
            map((path: AdcmTypedEntity[]) => setPath({ path })),
          );
        }),
      ),
  );

  constructor(
    private actions$: Actions,
    private detailService: ClusterService,
  ) {}

}
