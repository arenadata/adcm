import { Inject, Injectable } from '@angular/core';
import { Store } from '@ngrx/store';

import { socketClose, socketLost, socketOpen, socketResponse, StatusType } from '../store/socket/socket.actions';
import { SocketConfigService } from './socket-config.service';
import { SocketConfig } from '../socket/socket-config';

@Injectable()
export class SocketService {
  private socket: WebSocket;

  constructor(
    @Inject(SocketConfigService) public config: SocketConfig,
    private store: Store,
  ) {}

  init(openStatus: StatusType = StatusType.Open): WebSocket {
    this.socket = new WebSocket(this.config.serverEventUrl);

    this.socket.onopen = () => this.store.dispatch(socketOpen({ status: openStatus }));
    this.socket.onclose = () => this.store.dispatch(socketLost({ status: StatusType.Lost }));
    this.socket.onmessage = (response: MessageEvent) =>
      this.store.dispatch(socketResponse({ message: JSON.parse(response.data) }));

    return this.socket;
  }

  close(): void {
    if (this.socket) {
      this.socket.onclose = () => this.store.dispatch(socketClose({ status: StatusType.Close }));
      this.socket.close();
    }
  }

}
