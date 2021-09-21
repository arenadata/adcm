import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';

import { ConcernEventFilter, EventableService } from '@app/models/eventable-service';
import { EventMessage, selectMessage, SocketState } from '@app/core/store';

@Injectable()
export class ConcernService implements EventableService {

  constructor(
    private store: Store<SocketState>,
  ) { }

  parse(issueMessage: string): string[] {
    let result = [];
    for (const item of issueMessage.matchAll(/(.*?)(\$\{.+?\})|(.+$)/g)) {
      if (item.length) {
        result = [ ...result, ...item.slice(1, item.length) ];
      }
    }

    return result.filter(item => !!item);
  }

  events(eventFilter?: ConcernEventFilter): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      // filter(event => event?.object?.type === 'cluster-concerns'),
      filter(event => !eventFilter?.events || eventFilter.events.includes(event?.event)),
      filter(event => !eventFilter?.types || eventFilter.types.includes(event.object?.type)),
    );
  }

}
