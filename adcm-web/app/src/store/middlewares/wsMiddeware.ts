import type { Action, AnyAction, Dispatch, Middleware, MiddlewareAPI } from 'redux';
import { wsHost } from '@constants';
import type { AppStore, RootState } from '../store';
import { wsActions, wsCreateConfigActions } from './wsMiddleware.constants';
import type { ActionCreatorWithPayload } from '@reduxjs/toolkit';
import type { AdcmBackendEvent } from '@models/adcm';
import { WsClient } from '@api/wsClient/wsClient';
import { login, checkSession, logout } from '@store/authSlice';
import { createConfigrationEventHandle } from '@store/adcm/entityConfiguration/configurationSlice';

const wsClient = new WsClient(`${wsHost}/ws/event/`);

type WsActions = { [key: string]: ActionCreatorWithPayload<unknown> };

const wsActionSuccessHandle = (message: AdcmBackendEvent, thunkAPI: MiddlewareAPI<Dispatch<AnyAction>, AppStore>) => {
  if (wsCreateConfigActions.includes(message.event)) {
    createConfigrationEventHandle(message, thunkAPI);
  }
};

export const wsMiddleware: Middleware<
  // biome-ignore lint/complexity/noBannedTypes: <explanation>
  {},
  RootState
> = (storeApi) => {
  wsClient.onMessage = (event: MessageEvent<string>) => {
    const message: AdcmBackendEvent = JSON.parse(event.data);
    const wsAction = (wsActions as WsActions)[message.event];

    if (wsAction) {
      storeApi.dispatch(wsAction(message));
      wsActionSuccessHandle(message, storeApi);
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
