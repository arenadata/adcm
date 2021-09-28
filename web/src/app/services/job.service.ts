import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';
import { Store } from '@ngrx/store';

import { EventableService, EventFilter } from '@app/models/eventable-service';
import { EventMessage, selectMessage, SocketState } from '@app/core/store';

@Injectable()
export class JobService implements EventableService {

  constructor(
    private store: Store<SocketState>,
  ) {}

  events(eventFilter?: EventFilter): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === 'job'),
      filter(event => !eventFilter?.events || eventFilter.events.includes(event?.event)),
    );
  }

}
