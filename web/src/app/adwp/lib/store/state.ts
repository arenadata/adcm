import { AuthState } from './auth/auth.reducers';
import { SocketState } from './socket/socket.reducers';

export interface AdwpState {
  auth: AuthState;
  socket: SocketState;
  api?: any;
}
