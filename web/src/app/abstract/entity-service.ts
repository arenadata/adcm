import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';

export abstract class EntityService<T> {

  constructor(
    protected api: ApiService,
  ) {
  }

  abstract get(id: number, params: { [key: string]: string }): Observable<T>;

}
