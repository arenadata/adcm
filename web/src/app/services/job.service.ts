import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';
import { Store } from '@ngrx/store';

import { EventableService, EventFilter } from '@app/models/eventable-service';
import { EventMessage, selectMessage, SocketState } from '@app/core/store';
import { EntityService } from '@app/abstract/entity-service';
import { Job } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';

@Injectable()
export class JobService extends EntityService<Job> implements EventableService {

  constructor(
    private store: Store<SocketState>,
    protected api: ApiService,
  ) {
    super(api);
  }

  get(id: number, params: { [key: string]: string } = {}): Observable<Job> {
    return this.api.get(`${environment.apiRoot}job/${id}/`, params);
  }

  events(eventFilter?: EventFilter): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === 'job'),
      filter(event => !eventFilter?.events || eventFilter.events.includes(event?.event)),
    );
  }

}
