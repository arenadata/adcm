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
import { IRoot } from '@app/core/types/api';
import { Action, createAction, createFeatureSelector, createReducer, createSelector, on, props } from '@ngrx/store';

export const loadRoot = createAction('[API] LoadRoot');
export const loadStack = createAction('[API] LoadStack');
export const rootSuccess = createAction('[API] LoadRootSuccess', props<{ root: IRoot }>());
export const rootError = createAction('[API] LoadRootError');
export const stackSuccess = createAction('[API] LoadStackSuccess', props<{ stack: IRoot }>());

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
  on(rootError, state => ({ root: null, stack: null })),
  on(stackSuccess, (state, { stack }) => ({ ...state, stack }))
);

export function apiReducer(state: ApiState, action: Action) {
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
