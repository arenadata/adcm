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
import { EventMessage, getMessage, SocketState, clearMessages } from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { Subject } from 'rxjs';
import { filter, takeUntil, exhaust, share } from 'rxjs/operators';

@Directive({
  selector: '[appBase]',
})
export class BaseDirective implements OnDestroy {
  destroy$ = new Subject();

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  takeUntil<T>() {
    return takeUntil<T>(this.destroy$);
  }
}

export interface ISocketListener {
  socketListener: (m: EventMessage) => void;
}

@Directive({
    selector: '[appBase]',
})
@Injectable()
export class SocketListenerDirective extends BaseDirective implements OnDestroy {
  socket$ = this.socket.pipe(
    this.takeUntil(),
    select(getMessage),
    filter(m => !!m && !!m.object)    
  );

  constructor(private socket: Store<SocketState>) {
    super();
  }
   
  ngOnDestroy() {
    super.ngOnDestroy();
    this.socket.dispatch(clearMessages());
  }

  startListenSocket(): void {
    this.socket$.subscribe(m => this.socketListener(m));
  }

  socketListener(m: EventMessage) {
    console.warn('No implemented socketListener method', m);
  }
}
