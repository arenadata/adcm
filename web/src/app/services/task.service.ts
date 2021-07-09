import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { filter } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { IListResult } from '@adwp-ui/widgets';

import { EventMessage, EntityEvent, selectMessage, SocketState } from '@app/core/store';
import { EventableService } from '@app/models/eventable-service';
import { Task } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { EntityService } from '@app/abstract/entity-service';

@Injectable()
export class TaskService extends EntityService<Task> implements EventableService {

  constructor(
    private store: Store<SocketState>,
    protected api: ApiService,
  ) {
    super(api);
  }

  get(id: number, params: { [key: string]: string } = {}): Observable<Task> {
    return this.api.get(`api/v1/task/${id}/`, params);
  }

  list(params: { [key: string]: string } = {}): Observable<IListResult<Task>> {
    return this.api.get(`api/v1/task/`, params);
  }

  events(events: EntityEvent[]): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === 'task'),
      filter(event => !events || events.includes(event?.event)),
    );
  }

}
