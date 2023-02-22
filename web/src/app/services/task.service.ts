import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { filter } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { IListResult } from '@app/adwp';

import { EventMessage, selectMessage, SocketState } from '@app/core/store';
import { EventableService, EventFilter } from '@app/models/eventable-service';
import { Task } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { EntityService } from '@app/abstract/entity-service';
import { environment } from '@env/environment';

@Injectable()
export class TaskService extends EntityService<Task> implements EventableService {

  constructor(
    private store: Store<SocketState>,
    protected api: ApiService,
  ) {
    super(api);
  }

  get(id: number, params: { [key: string]: string } = {}): Observable<Task> {
    return this.api.get(`${environment.apiRoot}task/${id}/`, params);
  }

  list(params: { [key: string]: string } = {}): Observable<IListResult<Task>> {
    return this.api.get(`${environment.apiRoot}task/`, params);
  }

  events(eventFilter?: EventFilter, objectType?: string): Observable<EventMessage> {
    return this.store.pipe(
      selectMessage,
      filter(event => event?.object?.type === objectType),
      filter(event => !eventFilter?.events || eventFilter.events.includes(event?.event)),
    );
  }
}
