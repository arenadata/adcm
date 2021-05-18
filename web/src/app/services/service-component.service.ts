import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from '@app/core/api';
import { IServiceComponent } from '@app/models/service-component';
import { EntityService } from '@app/abstract/entity-service';

@Injectable({
  providedIn: 'root',
})
export class ServiceComponentService extends EntityService<IServiceComponent> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<IServiceComponent> {
    return this.api.get(`api/v1/component/${id}`, params);
  }

}
