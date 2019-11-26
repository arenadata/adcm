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
import { AuthService } from '@app/core/auth/auth.service';
import { environment } from '@env/environment';
import { Store } from '@ngrx/store';
import { EMPTY, of } from 'rxjs';

import { socketClose, socketOpen, socketResponse, SocketState, StatusType } from './socket.reducer';

@Injectable({
  providedIn: 'root',
})
export class SocketService {
  connectUrl = environment.SERVER_URL_EVENT;
  socket: WebSocket;

  constructor(private store: Store<SocketState>, private auth: AuthService) {}

  init(openStatus: StatusType = 'open') {
    if (!this.auth.token) {
      console.warn('Socket can not connect. Token is failed.');
      return EMPTY;
    }

    this.socket = new WebSocket(this.connectUrl, ['adcm', `${this.auth.token}`]);

    this.socket.onopen = () => this.store.dispatch(socketOpen({ status: openStatus }));
    this.socket.onclose = () => this.store.dispatch(socketClose({ status: 'close' }));
    this.socket.onmessage = (response: { data: string }) =>
      this.store.dispatch(socketResponse({ message: JSON.parse(response.data) }));

    console.log('Socket init');

    return of(this.socket);
  }

}
