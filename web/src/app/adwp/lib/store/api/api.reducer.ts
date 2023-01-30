import { Action, createAction, createFeatureSelector, createReducer, createSelector, on, props } from '@ngrx/store';

import { IRoot } from '../../models/root';

export const loadRoot = createAction('[API] LoadRoot');
export const loadStack = createAction('[API] LoadStack');
export const rootSuccess = createAction(
  '[API] LoadRootSuccess',
  props<{ root: IRoot }>()
);

export const rootError = createAction('[API] LoadRootError');

export const stackSuccess = createAction(
  '[API] LoadStackSuccess',
  props<{ stack: IRoot }>()
);

export interface ApiState {
  root: IRoot;
  stack: IRoot;
}

const InitState: ApiState = {
  root: null,
  stack: null,
};

const reducer = createReducer(
  InitState,
  on(rootSuccess, (state, { root }) => ({ ...state, root })),
  on(rootError, (state) => ({ root: null, stack: null })),
  on(stackSuccess, (state, { stack }) => ({ ...state, stack }))
);

export function apiReducer(state: ApiState, action: Action): ApiState {
  return reducer(state, action);
}

export const getApiState = createFeatureSelector<ApiState>('api');
export const getRoot = createSelector(
  getApiState,
  (state: ApiState) => state.root
);
export const getStack = createSelector(
  getApiState,
  (state: ApiState) => state.stack
);
