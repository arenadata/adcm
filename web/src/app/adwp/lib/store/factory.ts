import { ActionReducerMap } from '@ngrx/store';

import { AuthEffects } from './auth/auth.effects';
import { authReducer } from './auth/auth.reducers';
import { socketReducer } from './socket/socket.reducers';
import { AdwpState } from './state';

export class AdwpStoreFactory {

  static createReducers(): ActionReducerMap<AdwpState> {
    return {
      auth: authReducer,
      socket: socketReducer,
    };
  }

  static createEffects(): Array<any> {
    return [
      AuthEffects,
    ];
  }

}
