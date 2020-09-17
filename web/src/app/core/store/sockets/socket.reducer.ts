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
import { TypeName } from '@app/core/types';
import { Action, createAction, createFeatureSelector, createReducer, createSelector, on, props } from '@ngrx/store';

export interface IEMObject {
  type: TypeName;
  id: number;
  details: {
    id?: string;
    type: string;
    value: any;
  };
}

export interface EventMessage {
  event:
    | 'add'
    | 'add_job_log'
    | 'create'
    | 'delete'
    | 'remove'
    | 'change_config'
    | 'change_state'
    | 'change_status'
    | 'change_job_status'
    | 'change_hostcomponentmap'
    | 'raise_issue'
    | 'clear_issue'
    | 'upgrade';
  object?: IEMObject;
}

export type StatusType = 'open' | 'close' | 're-open';

export const socketInit = createAction('[Socket] Init');
export const socketOpen = createAction('[Socket] Open', props<{ status: StatusType }>());
export const socketClose = createAction('[Socket] Close', props<{ status: StatusType }>());
export const socketResponse = createAction('[Socket] Response', props<{ message: EventMessage }>());
export const clearMessages = createAction('[Socket] Clear messages');

export interface SocketState {
  status: StatusType;
  message: EventMessage;
}

const initialState: SocketState = {
  status: null,
  message: null,
};

const reducer = createReducer(
  initialState,
  on(socketInit, (state) => ({ ...state })),
  on(socketOpen, (state, { status }) => ({
    ...state,
    status,
  })),
  on(socketClose, (state, { status }) => ({
    ...state,
    status,
  })),
  on(socketResponse, (state, { message }) => ({
    ...state,
    message,
  })),
  on(clearMessages, (state) => ({ ...state, message: null }))
);

export function socketReducer(state: SocketState, action: Action) {
  return reducer(state, action);
}

export const getSocketState = createFeatureSelector<SocketState>('socket');
export const getConnectStatus = createSelector(getSocketState, (state: SocketState) => state.status);
export const getMessage = createSelector(getSocketState, (state) => state.message);
