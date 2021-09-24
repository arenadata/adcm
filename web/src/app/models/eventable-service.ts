import { Observable } from 'rxjs';

import { EntityEvent, EventMessage } from '@app/core/store';
import { ConcernEventType } from '@app/models/concern/concern-reason';

export interface EventFilter {
  events?: EntityEvent[];
}

export interface ConcernEventFilter extends EventFilter {
  types?: ConcernEventType[];
}

export interface EventableService {

  events(eventFilter?: EventFilter): Observable<EventMessage>;

}
