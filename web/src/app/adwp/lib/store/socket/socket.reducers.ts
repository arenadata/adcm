import { Action, createReducer, on } from '@ngrx/store';

import { StatusType, EventMessage, socketInit, socketOpen, socketClose, socketResponse, socketLost } from './socket.actions';

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
  on(socketLost, (state, { status }) => ({
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
);

export function socketReducer(state: SocketState, action: Action): SocketState {
  return reducer(state, action);
}
