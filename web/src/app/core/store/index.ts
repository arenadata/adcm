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
import { environment } from '@env/environment';
import { ActionReducerMap, MetaReducer } from '@ngrx/store';

import { ApiEffects } from '../api/api.effects';
import { apiReducer, ApiState } from '../api/api.reducer';
import { AuthEffects, authReducer, AuthState } from '../auth/auth.store';
import { IssueEffect, issueReducer, IssueState } from './issue';
import { ProfileEffects, profileReducer, ProfileState } from './profile';
import { SocketEffect } from './sockets/socket.effect';
import { socketReducer, SocketState } from './sockets/socket.reducer';
import { NavigationEffects, navigationReducer, NavigationState } from '@app/store/navigation/navigation.store';

export interface State {
  auth: AuthState;
  socket: SocketState;
  api: ApiState;
  profile: ProfileState;
  issue: IssueState;
  navigation: NavigationState,
}

export const reducers: ActionReducerMap<State> = {
  auth: authReducer,
  socket: socketReducer,
  api: apiReducer,
  profile: profileReducer,
  issue: issueReducer,
  navigation: navigationReducer,
};

export const metaReducers: MetaReducer<State>[] = !environment.production ? [] : [];

export const StoreEffects = [AuthEffects, ApiEffects, ProfileEffects, IssueEffect, SocketEffect, NavigationEffects];

export * from '../api/api.reducer';
export * from '../auth/auth.store';
export * from './profile';
export * from './profile/profile.service';
export * from './issue';
export * from './sockets/socket.service';
export * from './sockets/socket.reducer';
export * from '@app/store/navigation/navigation.store';
