import type { Action, Middleware } from 'redux';
import { wsHost } from '@constants';
import type { RootState } from '../store';
import { wsActions } from './wsMiddleware.constants';
import type { ActionCreatorWithPayload } from '@reduxjs/toolkit';
import type { AdcmBackendEvent } from '@models/adcm';
import { WsClient } from '@api/wsClient/wsClient';
import { login, checkSession, logout } from '@store/authSlice';

const wsClient = new WsClient(`${wsHost}/ws/event/`);

type WsActions = { [key: string]: ActionCreatorWithPayload<unknown> };

export const wsMiddleware: Middleware<
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  {},
  RootState
> = (storeApi) => {
  wsClient.onMessage = (event: MessageEvent<string>) => {
    const message: AdcmBackendEvent = JSON.parse(event.data);
    const wsAction = (wsActions as WsActions)[message.event];

    if (wsAction) {
      storeApi.dispatch(wsAction(message));
    }
  };

  return (next) => (action: Action) => {
    if (action.type === login.fulfilled.type || action.type === checkSession.fulfilled.type) {
      wsClient.open();
    }

    if (action.type === logout.fulfilled.type) {
      wsClient.close();
    }

    return next(action);
  };
};
