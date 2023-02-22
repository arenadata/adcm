import { createFeatureSelector, createSelector, select } from '@ngrx/store';
import { pipe } from 'rxjs';
import { skip } from 'rxjs/operators';

import { SocketState } from './socket.reducers';

export const getSocketState = createFeatureSelector<SocketState>('socket');
export const getConnectStatus = createSelector(getSocketState, (state: SocketState) => state.status);
export const getMessage = createSelector(getSocketState, (state) => state.message);
export const selectMessage = pipe(
  select(getMessage),
  skip(1),
);
