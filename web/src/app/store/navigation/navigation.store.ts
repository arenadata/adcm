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
import { concatMap, filter, map, switchMap, take, tap } from 'rxjs/operators';
import { Observable, zip } from 'rxjs';

import { AdcmEntity, AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { ServiceComponentService } from '@app/services/service-component.service';
import { EntityNames } from '@app/models/entity-names';
import { EventMessage, socketResponse } from '@app/core/store/sockets/socket.reducer';

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

export function getEventEntityType(type: string): TypeName {
  return type === 'component' ? 'servicecomponent' : <TypeName>type;
}

export function getPath(getters: Observable<AdcmTypedEntity>[]): Observable<Action> {
  return zip(...getters).pipe(
    map((path: AdcmTypedEntity[]) => setPath({ path })),
  );
}

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

          return getPath(getters);
        }),
      ),
  );

  changePathOfEvent$ = createEffect(() => this.actions$.pipe(
    ofType(socketResponse),
    filter(action => ['raise_issue', 'clear_issue'].includes(action.message.event)),
    tap(event => console.log('event', event)),
    concatMap((event: { message: EventMessage }) => {
      return new Observable<Action>(subscriber => {
        this.store.select(getNavigationPath).pipe(take(1)).subscribe((path) => {
          if (path.some(item => item.typeName === getEventEntityType(event.message.object.type) && event.message.object.id === item.id)) {
            this.entityGetter(event.message.object.type, event.message.object.id)
              .subscribe((entity) => {
                console.log(entity);
                subscriber.next(setPath({
                  path: path.reduce((acc, item) => acc.concat(item.id === event.message.object.id ? entity : item), []),
                }));
                subscriber.complete();
              }, () => subscriber.complete());
          } else {
            subscriber.complete();
          }
        }, () => subscriber.complete());
      });
    }),
  ));

  constructor(
    private actions$: Actions,
    private api: ApiService,
    private serviceComponentService: ServiceComponentService,
    private store: Store,
  ) {}

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
