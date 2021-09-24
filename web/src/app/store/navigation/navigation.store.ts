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
import { map } from 'rxjs/operators';
import { Observable, zip } from 'rxjs';

import { AdcmTypedEntity } from '@app/models/entity';
import { TypeName } from '@app/core/types';
import { ConcernEventType } from '@app/models/concern/concern-reason';


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
  switch (type) {
    case 'component':
      return 'servicecomponent';
    case ConcernEventType.Cluster:
      return 'cluster';
    case ConcernEventType.Service:
      return 'service';
    case ConcernEventType.ServiceComponent:
      return 'servicecomponent';
  }
}

export function getPath(getters: Observable<AdcmTypedEntity>[]): Observable<Action> {
  return zip(...getters).pipe(
    map((path: AdcmTypedEntity[]) => setPath({ path })),
  );
}

