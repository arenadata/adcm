import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';

import { EntityEvent, EventMessage, selectMessage, SocketState } from '../core/store';

@Injectable({
  providedIn: 'root'
})
export class ConcernService {

  constructor(
    private store: Store<SocketState>,
  ) { }

  events(events?: EntityEvent[]): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === 'cluster-concerns'),
      filter(event => !events || events.includes(event?.event)),
    );
  }

}
