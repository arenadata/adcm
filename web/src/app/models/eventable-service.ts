import { Observable } from 'rxjs';

import { EntityEvent, EventMessage } from '@app/core/store';
import { TypeName } from '@app/core/types';

export interface EventFilter {
  events?: EntityEvent[];
}

export interface ConcernEventFilter extends EventFilter {
  types?: TypeName[];
}

export interface EventableService {

  events(eventFilter?: EventFilter): Observable<EventMessage>;

}
