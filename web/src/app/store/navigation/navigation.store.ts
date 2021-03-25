import {
  Action,
  createAction,
  createFeatureSelector,
  createReducer,
  createSelector,
  on,
  props,
  Store,
} from '@ngrx/store';
import { ParamMap } from '@angular/router';
import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { filter, map, switchMap, tap, withLatestFrom } from 'rxjs/operators';
import { Observable, zip } from 'rxjs';
import { of } from 'rxjs/internal/observable/of';

import { AdcmEntity, AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { ServiceComponentService } from '@app/services/service-component.service';
import { EntityNames } from '@app/models/entity-names';
import { socketResponse } from '@app/core/store';

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
            const getter = this.entityGetter(param as TypeName, +action.params.get(param));
            if (getter) {
              acc.push(getter);
            }

            return acc;
          }, []);

          return this.getPath(getters);
        }),
      ),
  );

  changePathOfEvent$ = createEffect(() => this.actions$.pipe(
    ofType(socketResponse),
    filter(action => ['raise_issue', 'clear_issue'].includes(action.message.event)),
    withLatestFrom(this.store.select(getNavigationPath)),
    filter(
      ([action, path]) => path.some(
        item => item.typeName === this.getEventEntityType(action.message.object.type) && action.message.object.id === item.id
      )
    ),
    tap(([action, path]) => console.log(action, path)),
    switchMap(([action, path]) => {
      const getters: Observable<AdcmTypedEntity>[] = path.reduce((acc, entity) => {
        if (entity.typeName === this.getEventEntityType(action.message.object.type)) {
          const getter = this.entityGetter(entity.typeName, action.message.object.id);
          if (getter) {
            acc.push(getter);
          }
        } else {
          acc.push(of(entity));
        }

        return acc;
      }, []);

      return this.getPath(getters);
    }),
  ));

  constructor(
    private actions$: Actions,
    private api: ApiService,
    private serviceComponentService: ServiceComponentService,
    private store: Store,
  ) {}

  getEventEntityType(type: string): TypeName {
    return type === 'component' ? 'servicecomponent' : <TypeName>type;
  }

  getPath(getters: Observable<AdcmTypedEntity>[]): Observable<Action> {
    return zip(...getters).pipe(
      map((path: AdcmTypedEntity[]) => setPath({ path })),
    );
  }

  entityGetter(type: TypeName, id: number): Observable<AdcmTypedEntity> {
    const entityToTypedEntity = (getter: Observable<AdcmEntity>, typeName: TypeName) => getter.pipe(
      map(entity => ({
        ...entity,
        typeName,
      } as AdcmTypedEntity))
    );
    if (EntityNames.includes(type)) {
      if (type === 'servicecomponent') {
        return entityToTypedEntity(
          this.serviceComponentService.get(id),
          type,
        );
      } else {
        return entityToTypedEntity(
          this.api.getOne<any>(type, id),
          type,
        );
      }
    }
  }

}
