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
import { exhaustMap, map } from 'rxjs/operators';

import { State } from '../../store';
import { IUser, ProfileService } from './profile.service';

export type ProfileState = IUser;

const InitState = {
  username: '',
  change_password: '',
  profile: {
    dashboard: [],
    textarea: {},
    metrics: true, // deprecated
    settingsSaved: false,
  },
};

export const loadProfile = createAction('[Profile] Load');
export const clearProfile = createAction('[Profile] ClearProfile');
export const saveDashboard = createAction('[Profile] SaveDashboard', props<{ dashboard: any[] }>());
export const loadProfileSuccess = createAction('[Profile] LoadSuccess', props<{ profile: IUser }>());
export const setTextareaHeight = createAction('[Profile] SetTextareaHeight', props<{ key: string; value: number }>());
export const sendMetrics = createAction('[Profile] SendMetrics', props<{ metrics: boolean }>());
export const settingsSave = createAction('[Profile] SettingsSave', props<{ isSet: boolean }>());

const reducer = createReducer(
  InitState,
  on(loadProfileSuccess, (state, { profile }) => ({ ...profile })),
  on(setTextareaHeight, state => ({ ...state })),
  on(saveDashboard, (state, { dashboard }) => ({ ...state, dashboard })),
  on(sendMetrics, (state, { metrics }) => ({ ...state, metrics })),
  on(settingsSave, (state, { isSet }) => ({ ...state, isSet })),
  on(clearProfile, () => InitState)
);

export function profileReducer(state: ProfileState, action: Action) {
  return reducer(state, action);
}

@Injectable()
export class ProfileEffects {
  load$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadProfile),
      exhaustMap(() => this.service.getProfile().pipe(map(user => loadProfileSuccess({ profile: user }))))
    )
  );

  saveDashboard$ = createEffect(() =>
    this.actions$.pipe(
      ofType(saveDashboard),
      map(action => action.dashboard),
      exhaustMap(data =>
        this.service.setDashboardProfile(data).pipe(map(user => loadProfileSuccess({ profile: user })))
      )
    )
  );

  saveTextarea$ = createEffect(() =>
    this.actions$.pipe(
      ofType(setTextareaHeight),
      exhaustMap(a =>
        this.service.setTextareaProfile(a).pipe(map(user => loadProfileSuccess({ profile: user })))
      )
    )
  );

  sendMetrics$ = createEffect(() =>
    this.actions$.pipe(
      ofType(sendMetrics),
      map(a => this.service.setUser('metrics', a.metrics)),
      exhaustMap(() => this.service.setProfile().pipe(map(user => loadProfileSuccess({ profile: user }))))
    )
  );

  saveSettings$ = createEffect(() =>
    this.actions$.pipe(
      ofType(settingsSave),
      map(a => this.service.setUser('settingsSaved', a.isSet)),
      exhaustMap(() => this.service.setProfile().pipe(map(user => loadProfileSuccess({ profile: user }))))
    )
  );

  constructor(private actions$: Actions, private service: ProfileService, private store: Store<State>) {}
}

export const getProfileSelector = createFeatureSelector<ProfileState>('profile');

export const getProfile = createSelector(
  getProfileSelector,
  state => state.profile
);

export const getFirstAdminLogin = createSelector(
  getProfileSelector,
  state => state.username === 'admin' && !state.profile.settingsSaved
);

