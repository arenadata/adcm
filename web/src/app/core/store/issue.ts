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
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Action, createAction, createFeatureSelector, createReducer, createSelector, on, props, Store } from '@ngrx/store';
import { exhaustMap, filter, map, withLatestFrom } from 'rxjs/operators';

import { ApiService } from '../api';
import { State } from '../store';
import { ApiBase, Issue } from '../types';

export interface IssueState {
  value: Issue;
  url: string;
}

const InitState = {
  value: null,
  url: '',
};

export const loadIssue = createAction('[Issue] LoadIssue');
export const fillIssue = createAction('[Issue] FillIssue', props<{ value: Issue; url: string }>());

const reducer = createReducer(InitState, on(loadIssue, state => ({ ...state })), on(fillIssue, (state, { value, url }) => ({ value, url })));

export function issueReducer(state: IssueState, action: Action) {
  return reducer(state, action);
}

@Injectable()
export class IssueEffect {
  load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadIssue),
      withLatestFrom(this.store, (action, state) => state.issue.url),
      filter(url => !!url),
      exhaustMap(url => this.api.get<ApiBase>(url).pipe(map(o => fillIssue({ value: o.issue, url: o.url }))))
    )
  );

  constructor(private actions$: Actions, private api: ApiService, private store: Store<State>) {}
}

export const getIssueSelector = createFeatureSelector<IssueState>('issue');

export const checkIssue = createSelector(
  getIssueSelector,
  state => state
);
