import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { filter, tap } from 'rxjs/operators';
import { Store } from '@ngrx/store';

import { EventableService } from '@app/models/eventable-service';
import { EntityEvent, EventMessage, selectMessage, SocketState } from '@app/core/store';

@Injectable()
export class JobService implements EventableService {

  constructor(
    private store: Store<SocketState>,
  ) {}

  events(events?: EntityEvent[]): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === 'job'),
      filter(event => !events || events.includes(event?.event)),
    );
  }

}
