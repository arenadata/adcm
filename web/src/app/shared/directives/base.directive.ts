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
import { EventMessage, getMessage, SocketState } from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';

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

@Injectable()
export class SocketListener extends BaseDirective {
  socket$ = this.socket.pipe(
    select(getMessage),
    filter(m => !!m && !!m.object),
    this.takeUntil()
  );

  constructor(private socket: Store<SocketState>) {
    super();    
  }

  startListenSocket(): void {
    this.socket$.subscribe(m => this.socketListener(m));
  }

  socketListener(m: EventMessage) {
    console.warn('No implemented socketListener method', m);
  }
}
