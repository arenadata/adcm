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
import { Directive, Injectable, OnDestroy } from '@angular/core';
import { select, Store } from '@ngrx/store';
import { filter, tap } from 'rxjs/operators';
import { BaseDirective } from '@app/adwp';

import { EventMessage, getMessage, SocketState, clearMessages } from '@app/core/store';

@Directive({
  selector: '[appBase]',
})
@Injectable()
export class SocketListenerDirective extends BaseDirective implements OnDestroy {
  socket$ = this.socket.pipe(this.takeUntil(), select(getMessage), filter(m => !!m && !!m.object));

  constructor(private socket: Store<SocketState>) {
    super();
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    this.socket.dispatch(clearMessages());
  }

  startListenSocket(): void {
    this.socket$.pipe(
      tap(m => this.socketListener(m))
    ).subscribe();
  }

  socketListener(m: EventMessage) {
    console.warn('No implemented socketListener method', m);
  }
}
