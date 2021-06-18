import { Observable } from 'rxjs';

import { EntityEvent, EventMessage } from '@app/core/store';

export interface EventableService {

  events(events?: EntityEvent[]): Observable<EventMessage>;

}
