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
import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { filter, map, switchMap } from 'rxjs/operators';
import { Observable, zip } from 'rxjs';

import { AdcmEntity, AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { ServiceComponentService } from '@app/services/service-component.service';
import { EntityNames } from '@app/models/entity-names';

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
            const getter = this.entityGetter(param as TypeName, action.params);
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
    private api: ApiService,
    private serviceComponentService: ServiceComponentService,
  ) {}

  entityGetter(currentParam: TypeName, params: ParamMap): Observable<AdcmTypedEntity> {
    const entityToTypedEntity = (getter: Observable<AdcmEntity>, typeName: TypeName) => getter.pipe(
      map(entity => ({
        ...entity,
        typeName,
      } as AdcmTypedEntity))
    );
    if (EntityNames.includes(currentParam)) {
      if (currentParam === 'servicecomponent') {
        return entityToTypedEntity(
          this.serviceComponentService.get(+params.get(currentParam)),
          currentParam,
        );
      } else {
        return entityToTypedEntity(
          this.api.getOne<any>(currentParam, +params.get(currentParam)),
          currentParam,
        );
      }
    }
  }

}
